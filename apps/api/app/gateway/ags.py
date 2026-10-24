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
    )


def connect_sandbox(settings: Settings, sandbox_id: str) -> Sandbox:
    return Sandbox.connect(
        sandbox_id,
        api_key=settings.e2b.api_key,
        domain=settings.e2b.domain,
    )


def sandbox_host(sandbox: Sandbox) -> str:
    return sandbox.get_host(9000)
