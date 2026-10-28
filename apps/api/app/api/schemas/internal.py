from pydantic import BaseModel

from app.models.user_sandbox import SandboxStatus


class InternalSandboxEnsureResponse(BaseModel):
    sandbox_id: str
    status: SandboxStatus
