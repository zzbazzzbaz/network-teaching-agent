"""Agent 调用的内部服务间接口。

这些接口使用 X-Internal-Token 鉴权，只允许 agent 容器访问；
路由保持 /internal 前缀，不挂到 /api/v1，避免通过 nginx 公网暴露。
"""

from fastapi import APIRouter

from app.api.dependencies import InternalUserDep, SessionDep, SettingsDep
from app.api.schemas.internal import InternalSandboxEnsureResponse
from app.services import sandbox_service

router = APIRouter(tags=["internal-sandbox"], include_in_schema=False)


@router.post("/ensure", response_model=InternalSandboxEnsureResponse)
def ensure_sandbox_for_agent(
    session: SessionDep,
    settings: SettingsDep,
    user_id: InternalUserDep,
) -> InternalSandboxEnsureResponse:
    """确保指定用户有可用沙箱，并返回 agent 需要连接的 sandbox_id。"""
    info = sandbox_service.ensure_user_sandbox(
        user_id=user_id,
        session=session,
        settings=settings,
    )
    return InternalSandboxEnsureResponse(
        sandbox_id=info.sandbox_id,
        status=info.status,
    )
