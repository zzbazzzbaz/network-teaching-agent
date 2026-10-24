from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SandboxResponse(BaseModel):
    sandbox_id: str
    status: Literal["running"] = "running"
    vscode_url: str
    ttyd_url: str
    expires_at: datetime
