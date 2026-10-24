from e2b import Sandbox

from core.config import get_settings


def connect_sandbox(sandbox_id: str) -> Sandbox:
    settings = get_settings()
    return Sandbox.connect(
        sandbox_id=sandbox_id, api_key=settings.e2b_api_key, domain=settings.e2b_domain
    )
