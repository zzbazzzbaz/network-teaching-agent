from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SandboxResponse(BaseModel):
    sandbox_id: str
    status: Literal["running", "paused", "stopping"]
    vscode_url: str | None
    ttyd_url: str | None
    expires_at: datetime
    last_active_at: datetime
    paused_at: datetime | None
    hard_destroy_at: datetime
    heartbeat_seconds: int
