"""API 依赖注入。

对外只暴露 XxxDep 别名；内部实现函数统一以 _ 开头。
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.core.security import decode_access_token
from app.gateway.agent import AgentGateway
from app.repositories.user_repository import user_repository


def _get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


SessionDep = Annotated[Session, Depends(_get_session)]


def _get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


SettingsDep = Annotated[Settings, Depends(_get_settings)]


def _get_agent(request: Request) -> AgentGateway:
    return cast(AgentGateway, request.app.state.agent)


AgentDep = Annotated[AgentGateway, Depends(_get_agent)]


def _get_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _require_user(request: Request) -> uuid.UUID:
    token = _get_bearer_token(request)
    if token is None:
        raise HTTPException(status_code=401, detail="缺少登录凭证")
    try:
        return decode_access_token(token)
    except AppError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


UserIdDep = Annotated[uuid.UUID, Depends(_require_user)]


def _require_internal_token(request: Request, settings: SettingsDep) -> None:
    token = request.headers.get("X-Internal-Token")
    if not token:
        raise HTTPException(status_code=401, detail="缺少内部凭证")
    if not secrets.compare_digest(token, settings.server.auth_token):
        raise HTTPException(status_code=403, detail="内部凭证无效")


def _require_internal_user(
    x_user_id: Annotated[uuid.UUID, Header(alias="X-User-Id")],
    session: SessionDep,
    _internal_token: Annotated[None, Depends(_require_internal_token)],
) -> uuid.UUID:
    """先校验内部 token，再校验 X-User-Id 对应账号存在且启用。"""
    user = user_repository.get(session, x_user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    if not user.status:
        raise ForbiddenError("用户已禁用")
    return x_user_id


InternalUserDep = Annotated[uuid.UUID, Depends(_require_internal_user)]

__all__ = [
    "AgentDep",
    "InternalUserDep",
    "SessionDep",
    "SettingsDep",
    "UserIdDep",
]
