"""内部服务间路由汇总。

这些接口只允许 agent 容器访问，统一使用 X-Internal-Token；
路由保持 /internal 前缀，不挂 /api/v1，避免通过 nginx 公网暴露。
"""

from fastapi import APIRouter

from app.api.internal import files, question_bank, sandbox, sessions

router = APIRouter(prefix="/internal", include_in_schema=False)
router.include_router(sandbox.router, prefix="/sandbox")
router.include_router(question_bank.router, prefix="/question-bank")
router.include_router(sessions.router, prefix="/sessions")
router.include_router(files.router, prefix="/files")
