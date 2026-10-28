import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.api.schemas.base import ApiRequest, ApiResponse
from app.api.schemas.pagination import Page, PageQuery
from app.core.constants import MAX_SESSION_TITLE_LENGTH

AgentId = Literal["exp_agent", "teach_agent"]


class CreateSessionBody(ApiRequest):
    title: str = Field(default="", max_length=MAX_SESSION_TITLE_LENGTH)
    agent_id: AgentId


class UpdateSessionBody(ApiRequest):
    title: str = Field(max_length=MAX_SESSION_TITLE_LENGTH)


class SessionListQuery(PageQuery):
    limit: int = Field(default=20, ge=1, le=50)
    agent_id: AgentId | None = None


class SessionResponse(ApiResponse):
    session_id: uuid.UUID
    agent_id: AgentId
    title: str
    created_at: datetime
    updated_at: datetime


class SessionPageResponse(Page[SessionResponse]):
    pass
