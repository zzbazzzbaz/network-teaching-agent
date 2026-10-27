from uuid import UUID

from pydantic import BaseModel

from app.models.user_sandbox import SandboxStatus


class InternalSandboxEnsureRequest(BaseModel):
    user_id: UUID


class InternalSandboxEnsureResponse(BaseModel):
    sandbox_id: str
    status: SandboxStatus
