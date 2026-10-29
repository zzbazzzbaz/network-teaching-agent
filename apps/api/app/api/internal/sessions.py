"""Agent 调用的内部会话接口。

这些接口使用 X-Internal-Token 鉴权，只允许 agent 容器访问；
路由保持 /internal 前缀，不挂到 /api/v1，避免通过 nginx 公网暴露。
"""

import logging
import uuid

from fastapi import APIRouter

from app.api.dependencies import InternalUserDep, SessionDep
from app.api.schemas.internal import (
    InternalSessionTitleRequest,
    InternalSessionTitleResponse,
)
from app.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal-sessions"], include_in_schema=False)


@router.post("/{session_id}/title", response_model=InternalSessionTitleResponse)
def set_session_title(
    session_id: uuid.UUID,
    body: InternalSessionTitleRequest,
    session: SessionDep,
    user_id: InternalUserDep,
) -> InternalSessionTitleResponse:
    chat_session, updated = session_service.auto_title_session(
        owner_id=user_id,
        session_id=session_id,
        title=body.title,
        session=session,
    )
    reason = "updated" if updated else "not_default"
    logger.info(
        "会话自动标题 session_id=%s updated=%s reason=%s title_len=%s",
        session_id,
        updated,
        reason,
        len(chat_session.title),
    )
    return InternalSessionTitleResponse(
        updated=updated,
        title=chat_session.title,
        reason=reason,
    )
