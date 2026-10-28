from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import SettingsDep, UserIdDep
from app.api.schemas.memory import MemoryFileQuery, MemoryFileResponse, MemoryTreeResponse
from app.services.memory_service import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/tree", response_model=MemoryTreeResponse, summary="获取我的记忆目录")
def get_memory_tree(
    user_id: UserIdDep,
    settings: SettingsDep,
) -> MemoryTreeResponse:
    return memory_service.get_tree(user_id=user_id, settings=settings)


@router.get("/file", response_model=MemoryFileResponse, summary="读取我的记忆文件")
def get_memory_file(
    params: Annotated[MemoryFileQuery, Query()],
    user_id: UserIdDep,
    settings: SettingsDep,
) -> MemoryFileResponse:
    return memory_service.get_file(
        user_id=user_id,
        path=params.path,
        settings=settings,
    )
