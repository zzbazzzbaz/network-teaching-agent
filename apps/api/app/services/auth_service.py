import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import (
    MAX_PASSWORD_BYTES,
    MAX_USERNAME_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_USERNAME_LENGTH,
)
from app.core.exceptions import ForbiddenError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import Users
from app.repositories.user_repository import user_repository


def _validate_username(username: str) -> str:
    resolved = username.strip()
    if not (MIN_USERNAME_LENGTH <= len(resolved) <= MAX_USERNAME_LENGTH):
        raise ValidationError(
            f"用户名长度须为 {MIN_USERNAME_LENGTH}-{MAX_USERNAME_LENGTH} 个字符"
        )
    return resolved


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"密码长度至少 {MIN_PASSWORD_LENGTH} 位")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValidationError("密码过长（UTF-8 编码不超过 72 字节）")


def _issue_tokens(user_id: str) -> dict[str, Any]:
    access_token, expires_in = create_access_token(user_id)
    return {
        "access_token": access_token,
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "expires_in": expires_in,
    }


def login(*, username: str, password: str, session: Session) -> dict[str, Any]:
    user = user_repository.get_by_username(session, username.strip())
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误")
    if not user.status:
        raise ForbiddenError("账号已被禁用")
    return {
        "user_id": user.user_id,
        "username": user.username,
        **_issue_tokens(str(user.user_id)),
    }


def refresh(*, refresh_token: str, session: Session) -> dict[str, Any]:
    user_id = decode_refresh_token(refresh_token)
    user = user_repository.get(session, user_id)
    if user is None:
        raise UnauthorizedError("账号不存在")
    if not user.status:
        raise ForbiddenError("账号已被禁用")
    return {
        "user_id": user.user_id,
        "username": user.username,
        **_issue_tokens(str(user.user_id)),
    }


def get_user(*, user_id: uuid.UUID, session: Session) -> Users:
    user = user_repository.get(session, user_id)
    if user is None:
        raise UnauthorizedError("账号不存在")
    if not user.status:
        raise ForbiddenError("账号已被禁用")
    return user


def create_user(*, username: str, password: str, session: Session) -> Users:
    """仅供管理命令使用；HTTP 层不暴露注册接口。"""
    resolved = _validate_username(username)
    validate_password(password)
    if user_repository.get_by_username(session, resolved) is not None:
        raise ValidationError("用户名已被占用")
    return user_repository.create(
        session,
        username=resolved,
        password_hash=hash_password(password),
    )
