"""当前登录用户的会话管理接口。

所有操作都用 JWT 中的 user_id 做 owner 过滤，不能访问其他用户的会话。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.dependencies import SessionDep, UserIdDep
from app.api.schemas.session import (
    CreateSessionBody,
    SessionListQuery,
    SessionPageResponse,
    SessionResponse,
    UpdateSessionBody,
)
from app.core.pagination import PageRequest
from app.models.session import ChatSession
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionPageResponse, summary="列出我的会话")
def list_sessions(
    params: Annotated[SessionListQuery, Query()],
    session: SessionDep,
    user_id: UserIdDep,
) -> SessionPageResponse:
    page = PageRequest(limit=params.limit, offset=params.offset)
    result = session_service.list_sessions(
        owner_id=user_id,
        session=session,
        page=page,
        agent_id=params.agent_id,
    )
    return SessionPageResponse(
        items=[_to_response(item) for item in result.items],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.post("", response_model=SessionResponse, status_code=201, summary="创建会话")
def create_session(
    body: CreateSessionBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> SessionResponse:
    """为当前用户创建新会话。

    标题为空时使用默认标题；`agent_id` 必须显式指定，返回创建的会话及 201 状态。
    """
    chat_session = session_service.create_session(
        owner_id=user_id,
        agent_id=body.agent_id,
        title=body.title,
        session=session,
    )
    return _to_response(chat_session)


@router.get("/{session_id}", response_model=SessionResponse, summary="获取会话")
def get_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> SessionResponse:
    return _to_response(
        session_service.get_owned_session(
            owner_id=user_id,
            session_id=session_id,
            session=session,
        )
    )


@router.patch("/{session_id}", response_model=SessionResponse, summary="重命名会话")
def rename_session(
    session_id: uuid.UUID,
    body: UpdateSessionBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> SessionResponse:
    return _to_response(
        session_service.rename_session(
            owner_id=user_id,
            session_id=session_id,
            title=body.title,
            session=session,
        )
    )


@router.post("/{session_id}/touch", status_code=204, summary="刷新会话活跃时间")
def touch_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> Response:
    session_service.touch_session(owner_id=user_id, session_id=session_id, session=session)
    return Response(status_code=204)


@router.delete("/{session_id}", status_code=204, summary="删除会话")
def delete_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> Response:
    session_service.delete_session(owner_id=user_id, session_id=session_id, session=session)
    return Response(status_code=204)


def _to_response(chat_session: ChatSession) -> SessionResponse:
    return SessionResponse.model_validate(chat_session)
