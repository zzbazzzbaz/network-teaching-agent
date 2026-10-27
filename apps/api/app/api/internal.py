from fastapi import APIRouter

from app.api.dependencies import InternalTokenDep, SessionDep, SettingsDep
from app.api.schemas.internal import (
    InternalSandboxEnsureRequest,
    InternalSandboxEnsureResponse,
)
from app.core.exceptions import ForbiddenError, NotFoundError
from app.repositories.user_repository import user_repository
from app.services import sandbox_service

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.post("/sandbox/ensure", response_model=InternalSandboxEnsureResponse)
def ensure_sandbox_for_agent(
    payload: InternalSandboxEnsureRequest,
    session: SessionDep,
    settings: SettingsDep,
    _internal_token: InternalTokenDep,
) -> InternalSandboxEnsureResponse:
    user = user_repository.get(session, payload.user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    if not user.status:
        raise ForbiddenError("用户已禁用")

    info = sandbox_service.ensure_user_sandbox(
        user_id=payload.user_id,
        session=session,
        settings=settings,
    )
    return InternalSandboxEnsureResponse(
        sandbox_id=info.sandbox_id,
        status=info.status,
    )
