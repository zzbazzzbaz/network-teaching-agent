from e2b import Sandbox

from app.core.config import Settings


def create_sandbox(settings: Settings, *, user_id: str) -> Sandbox:
    return Sandbox.create(
        template=settings.ags.tool_name,
        timeout=settings.ags.sandbox_timeout_seconds,
        api_key=settings.e2b.api_key,
        domain=settings.e2b.domain,
        metadata={"user_id": user_id},
        network={"allow_public_traffic": True},
        # AGS timeout 作为最后兜底：暂停而不是 kill，避免 workspace 丢失。
        # 正常情况下 reaper 会先按 30 分钟空闲主动 pause。
        lifecycle={"on_timeout": "pause", "auto_resume": False},
    )


def connect_sandbox(
    settings: Settings,
    sandbox_id: str,
    *,
    timeout: int | None = None,
) -> Sandbox:
    return Sandbox.connect(
        sandbox_id,
        timeout=timeout,
        api_key=settings.e2b.api_key,
        domain=settings.e2b.domain,
    )


def pause_sandbox(settings: Settings, sandbox_id: str) -> bool:
    return Sandbox.pause(
        sandbox_id,
        api_key=settings.e2b.api_key,
        domain=settings.e2b.domain,
    )


def kill_sandbox(settings: Settings, sandbox_id: str) -> bool:
    return Sandbox.kill(
        sandbox_id,
        api_key=settings.e2b.api_key,
        domain=settings.e2b.domain,
    )


def sandbox_host(settings: Settings, sandbox_id: str) -> str:
    """AGS 公网链接格式与 E2B Sandbox.get_host 保持一致。"""
    return f"9000-{sandbox_id}.{settings.e2b.domain}"
