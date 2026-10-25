from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

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


@router.post("/heartbeat", response_model=SandboxResponse)
def heartbeat_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    info = sandbox_service.heartbeat_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return _to_response(info)


@router.post("/pause", response_model=SandboxResponse)
def pause_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    info = sandbox_service.pause_user_sandbox(
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
    deleted = sandbox_service.delete_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    if deleted is sandbox_service.DeleteResult.STOPPING:
        return JSONResponse(status_code=202, content={"status": "stopping"})
    return Response(status_code=204)


def _to_response(info: sandbox_service.SandboxInfo) -> SandboxResponse:
    return SandboxResponse(
        sandbox_id=info.sandbox_id,
        status=info.status,
        vscode_url=info.vscode_url,
        ttyd_url=info.ttyd_url,
        expires_at=info.expires_at,
        last_active_at=info.last_active_at,
        paused_at=info.paused_at,
        hard_destroy_at=info.hard_destroy_at,
        heartbeat_seconds=info.heartbeat_seconds,
    )
