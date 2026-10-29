from typing import Literal

from pydantic import Field

from app.api.schemas.base import ApiRequest, ApiResponse
from app.core.constants import MAX_SESSION_TITLE_LENGTH
from app.models.user_sandbox import SandboxStatus


class InternalSandboxEnsureResponse(ApiResponse):
    sandbox_id: str
    status: SandboxStatus


class InternalSessionTitleRequest(ApiRequest):
    title: str = Field(min_length=1, max_length=MAX_SESSION_TITLE_LENGTH)


class InternalSessionTitleResponse(ApiResponse):
    updated: bool
    title: str
    reason: Literal["updated", "not_default"]
