"""当前登录用户的会话管理接口。

所有操作都用 JWT 中的 user_id 做 owner 过滤，不能访问其他用户的会话。
"""

import uuid

from fastapi import APIRouter, Response

from app.api.dependencies import SessionDep, UserIdDep
from app.api.schemas.session import CreateSessionBody, SessionResponse, UpdateSessionBody
from app.models.session import ChatSession
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse], summary="列出我的会话")
def list_sessions(session: SessionDep, user_id: UserIdDep) -> list[ChatSession]:
    """列出当前用户的所有会话，按最近更新时间倒序排列。"""
    return session_service.list_sessions(owner_id=user_id, session=session)


@router.post("", response_model=SessionResponse, status_code=201, summary="创建会话")
def create_session(
    body: CreateSessionBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> ChatSession:
    """为当前用户创建新会话。

    标题为空时使用默认标题；返回创建的会话及 201 状态。
    """
    return session_service.create_session(owner_id=user_id, title=body.title, session=session)


@router.get("/{session_id}", response_model=SessionResponse, summary="获取会话")
def get_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> ChatSession:
    """获取当前用户拥有的指定会话；不存在或不属于当前用户时返回 404。"""
    return session_service.get_owned_session(
        owner_id=user_id,
        session_id=session_id,
        session=session,
    )


@router.patch("/{session_id}", response_model=SessionResponse, summary="重命名会话")
def rename_session(
    session_id: uuid.UUID,
    body: UpdateSessionBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> ChatSession:
    """修改当前用户拥有的会话标题；空标题会回退到默认标题。"""
    return session_service.rename_session(
        owner_id=user_id,
        session_id=session_id,
        title=body.title,
        session=session,
    )


@router.post("/{session_id}/touch", status_code=204, summary="刷新会话活跃时间")
def touch_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> Response:
    """更新会话的 updated_at，用于让最近使用的会话排在列表前面。"""
    session_service.touch_session(owner_id=user_id, session_id=session_id, session=session)
    return Response(status_code=204)


@router.delete("/{session_id}", status_code=204, summary="删除会话")
def delete_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> Response:
    """删除当前用户拥有的会话；不存在或不属于当前用户时返回 404。"""
    session_service.delete_session(owner_id=user_id, session_id=session_id, session=session)
    return Response(status_code=204)
