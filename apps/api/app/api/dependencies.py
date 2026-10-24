import uuid
from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.security import decode_access_token


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_settings_dep(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _bearer(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def require_user(request: Request) -> uuid.UUID:
    token = _bearer(request)
    if token is None:
        raise HTTPException(status_code=401, detail="缺少登录凭证")
    try:
        return decode_access_token(token)
    except AppError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
UserIdDep = Annotated[uuid.UUID, Depends(require_user)]
