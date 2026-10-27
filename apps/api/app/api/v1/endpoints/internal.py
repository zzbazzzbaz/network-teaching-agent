"""Agent 调用的内部服务间接口。

这些接口使用 X-Internal-Token 鉴权，只允许 agent 容器访问；
路由保持 /internal 前缀，不挂到 /api/v1，避免通过 nginx 公网暴露。
"""

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
    """确保指定用户有可用沙箱，并返回 agent 需要连接的 sandbox_id。

    - 由 agent 使用服务 token 调用，不依赖浏览器 JWT；
    - 用户不存在返回 404，用户被禁用返回 403；
    - 创建、恢复、续期和轮换均复用 sandbox_service.ensure_user_sandbox。
    """
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
