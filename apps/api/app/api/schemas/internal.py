from app.api.schemas.base import ApiResponse
from app.models.user_sandbox import SandboxStatus


class InternalSandboxEnsureResponse(ApiResponse):
    sandbox_id: str
    status: SandboxStatus
