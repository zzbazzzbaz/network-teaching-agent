"""当前登录用户的账户沙箱接口。

前端使用这些接口展示沙箱状态、启动/恢复、心跳续期、暂停和销毁。
Agent 不再通过这些接口保证运行时可用性，而是使用内部接口
``POST /internal/sandbox/ensure``；两边最终都调用 sandbox_service。
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.api.dependencies import SessionDep, SettingsDep, UserIdDep
from app.api.schemas.sandbox import SandboxResponse
from app.services import sandbox_service

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.get("", response_model=SandboxResponse, summary="查询账户沙箱")
def get_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    """只读查询当前用户的沙箱状态。

    不创建沙箱、不连接 AGS，也不触发续期；沙箱记录不存在时返回 404。
    """
    info = sandbox_service.get_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return _to_response(info)


@router.post("", response_model=SandboxResponse, summary="启动或恢复账户沙箱")
def ensure_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    """确保当前用户有可用沙箱。

    用于前端“启动/恢复”按钮和打开 VSCode/ttyd 前显式调用：
    - 无记录时创建；
    - running 时续期；
    - paused 时恢复；
    - 超过生命周期或暂停保留期时先销毁再创建。
    """
    info = sandbox_service.ensure_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return _to_response(info)


@router.post("/heartbeat", response_model=SandboxResponse, summary="沙箱心跳续期")
def heartbeat_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    """为当前用户的 running 沙箱续期。

    与 ensure 的区别是：心跳不会创建沙箱；沙箱已暂停时只返回 paused 状态，
    不会自动恢复。前端在 running 状态下每 5 分钟调用一次。
    """
    info = sandbox_service.heartbeat_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return _to_response(info)


@router.post("/pause", response_model=SandboxResponse, summary="暂停账户沙箱")
def pause_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> SandboxResponse:
    """暂停当前用户的沙箱并保留 workspace。

    已暂停时幂等返回 paused；沙箱不存在时返回 404。
    """
    info = sandbox_service.pause_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return _to_response(info)


@router.delete("", status_code=204, summary="销毁账户沙箱")
def delete_sandbox(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> Response:
    """销毁当前用户的沙箱及其 workspace。

    删除是异步的：正在销毁时返回 202 + ``{"status": "stopping"}``；
    已删除或本来不存在时返回 204。
    """
    deleted = sandbox_service.delete_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    if deleted is sandbox_service.DeleteResult.STOPPING:
        return JSONResponse(status_code=202, content={"status": "stopping"})
    return Response(status_code=204)


def _to_response(info: sandbox_service.SandboxInfo) -> SandboxResponse:
    """把服务层 SandboxInfo 映射为公开沙箱接口响应。"""
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
