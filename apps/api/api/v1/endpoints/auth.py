from typing import Any

from fastapi import APIRouter

from api.dependencies import SessionDep, UserIdDep
from api.schemas.auth import AuthResponse, LoginBody, RefreshBody, UserResponse
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(body: LoginBody, session: SessionDep) -> dict[str, Any]:
    return auth_service.login(username=body.username, password=body.password, session=session)


@router.post("/refresh", response_model=AuthResponse)
def refresh(body: RefreshBody, session: SessionDep) -> dict[str, Any]:
    return auth_service.refresh(refresh_token=body.refresh_token, session=session)


@router.get("/me", response_model=UserResponse)
def me(user_id: UserIdDep, session: SessionDep) -> dict[str, Any]:
    user = auth_service.get_user(user_id=user_id, session=session)
    return {"user_id": user.user_id, "username": user.username}
