from datetime import datetime
from typing import Literal

from app.api.schemas.base import ApiResponse
from app.models.user_sandbox import SandboxStatus


class SandboxResponse(ApiResponse):
    sandbox_id: str
    status: SandboxStatus
    vscode_url: str | None
    ttyd_url: str | None
    expires_at: datetime
    last_active_at: datetime
    paused_at: datetime | None
    hard_destroy_at: datetime
    heartbeat_seconds: int


class SandboxDeleteResponse(ApiResponse):
    status: Literal["stopping"]
