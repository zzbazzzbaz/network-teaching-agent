import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateSessionBody(BaseModel):
    title: str = ""


class UpdateSessionBody(BaseModel):
    title: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
