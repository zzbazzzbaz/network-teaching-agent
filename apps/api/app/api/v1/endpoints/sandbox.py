from fastapi import APIRouter, Response

from app.api.dependencies import SessionDep, SettingsDep, UserIdDep
from app.api.schemas.sandbox import SandboxResponse
from app.services import sandbox_service

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.get("", response_model=SandboxResponse)
def get_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    info = sandbox_service.get_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return _to_response(info)


@router.post("", response_model=SandboxResponse)
def ensure_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    info = sandbox_service.ensure_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return _to_response(info)


@router.delete("", status_code=204)
def delete_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> Response:
    sandbox_service.delete_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return Response(status_code=204)


def _to_response(info: sandbox_service.SandboxInfo) -> SandboxResponse:
    return SandboxResponse(
        sandbox_id=info.sandbox_id,
        vscode_url=info.vscode_url,
        ttyd_url=info.ttyd_url,
        expires_at=info.expires_at,
    )
