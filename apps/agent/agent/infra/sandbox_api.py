from dataclasses import dataclass
from typing import Any

import httpx


class SandboxApiError(RuntimeError):
    """API 无法提供当前用户可用沙箱。"""


@dataclass(frozen=True, slots=True)
class ResolvedSandbox:
    sandbox_id: str
    status: str


class SandboxApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        internal_token: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._internal_token = internal_token
        self._timeout_seconds = timeout_seconds

    def ensure_user_sandbox(self, user_id: str) -> ResolvedSandbox:
        if not self._internal_token:
            raise SandboxApiError("AGENT_INTERNAL_TOKEN 未配置")

        try:
            response = httpx.post(
                f"{self._base_url}/internal/sandbox/ensure",
                json={"user_id": user_id},
                headers={"X-Internal-Token": self._internal_token},
                timeout=self._timeout_seconds,
            )
        except (httpx.HTTPError, ValueError) as e:
            raise SandboxApiError("沙箱服务暂不可用，请稍后重试") from e

        if response.status_code != 200:
            raise SandboxApiError(_error_message(response))

        try:
            payload = response.json()
        except ValueError as e:
            raise SandboxApiError("沙箱服务返回了无效响应") from e

        sandbox_id = payload.get("sandbox_id") if isinstance(payload, dict) else None
        if not isinstance(sandbox_id, str) or not sandbox_id:
            raise SandboxApiError("沙箱服务未返回 sandbox_id")

        status = payload.get("status")
        return ResolvedSandbox(
            sandbox_id=sandbox_id,
            status=status if isinstance(status, str) else "running",
        )


def _error_message(response: httpx.Response) -> str:
    detail = ""
    try:
        payload: Any = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        detail = f": {payload['detail']}"
    return f"沙箱服务返回 {response.status_code}{detail}"
