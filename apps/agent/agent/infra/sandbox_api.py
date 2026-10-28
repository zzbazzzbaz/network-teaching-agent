import httpx

from agent.core.config import get_settings


class SandboxApiError(RuntimeError):
    """API 无法提供当前用户可用沙箱。"""


def ensure_sandbox_id(user_id: str) -> str:
    """调用 API 确保用户沙箱可用，并返回当前 sandbox_id。"""
    settings = get_settings()
    base_url = settings.server.api_base_url.rstrip("/")

    try:
        response = httpx.post(
            f"{base_url}/internal/sandbox/ensure",
            headers={
                "X-Internal-Token": settings.server.auth_token,
                "X-User-Id": user_id,
            },
            timeout=settings.server.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as e:
        raise SandboxApiError(f"沙箱服务返回 {e.response.status_code}") from e
    except (httpx.HTTPError, ValueError) as e:
        raise SandboxApiError("沙箱服务暂不可用，请稍后重试") from e

    sandbox_id = payload.get("sandbox_id") if isinstance(payload, dict) else None
    if not isinstance(sandbox_id, str) or not sandbox_id:
        raise SandboxApiError("沙箱服务未返回 sandbox_id")
    return sandbox_id
