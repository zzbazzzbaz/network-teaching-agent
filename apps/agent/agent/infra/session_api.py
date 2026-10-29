from __future__ import annotations

from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from agent.core.config import get_settings


class SessionTitleError(RuntimeError):
    """API 自动标题接口不可用或返回错误。"""


class SessionTitleNotFound(SessionTitleError):
    """会话不存在或已删除。"""


class SessionTitleResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    updated: bool
    title: str
    reason: Literal["updated", "not_default"]


async def set_session_title(
    *,
    user_id: str,
    thread_id: str,
    title: str,
) -> SessionTitleResult:
    settings = get_settings()
    base_url = settings.server.api_base_url.rstrip("/")
    headers = {
        "X-Internal-Token": settings.server.auth_token,
        "X-User-Id": user_id,
    }

    try:
        async with httpx.AsyncClient(
            timeout=min(settings.server.timeout_seconds, 5)
        ) as client:
            response = await client.post(
                f"{base_url}/internal/sessions/{thread_id}/title",
                json={"title": title},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise SessionTitleNotFound("会话不存在") from e
        raise SessionTitleError(
            f"标题服务返回 {e.response.status_code}"
        ) from e
    except (httpx.HTTPError, ValueError) as e:
        raise SessionTitleError("标题服务暂不可用") from e

    try:
        return SessionTitleResult.model_validate(payload)
    except ValidationError as e:
        raise SessionTitleError("标题服务响应格式错误") from e
