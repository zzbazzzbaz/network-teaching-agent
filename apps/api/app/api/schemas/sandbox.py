from datetime import datetime

from pydantic import BaseModel

from app.models.user_sandbox import SandboxStatus


class SandboxResponse(BaseModel):
    sandbox_id: str
    status: SandboxStatus
    vscode_url: str | None
    ttyd_url: str | None
    expires_at: datetime
    last_active_at: datetime
    paused_at: datetime | None
    hard_destroy_at: datetime
    heartbeat_seconds: int
