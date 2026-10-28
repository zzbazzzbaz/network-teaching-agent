from fastapi import APIRouter

from app.api.dependencies import SessionDep, UserIdDep
from app.api.schemas.auth import AuthResponse, LoginBody, RefreshBody, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(body: LoginBody, session: SessionDep) -> AuthResponse:
    return AuthResponse.model_validate(
        auth_service.login(username=body.username, password=body.password, session=session)
    )


@router.post("/refresh", response_model=AuthResponse)
def refresh(body: RefreshBody, session: SessionDep) -> AuthResponse:
    return AuthResponse.model_validate(
        auth_service.refresh(refresh_token=body.refresh_token, session=session)
    )


@router.get("/me", response_model=UserResponse)
def me(user_id: UserIdDep, session: SessionDep) -> UserResponse:
    user = auth_service.get_user(user_id=user_id, session=session)
    return UserResponse.model_validate(user)
