from __future__ import annotations

import asyncio
from uuid import UUID

import httpx
from pydantic import BaseModel

from agent.core.config import get_settings

FILE_TIMEOUT_SECONDS = 10.0
RETRY_DELAY_SECONDS = 0.2


class FileApiError(RuntimeError):
    """图片服务不可用或返回错误。"""


class FileNotFound(FileApiError):
    """图片不存在或不属于当前用户。"""


class FileMetadata(BaseModel):
    file_id: UUID
    name: str
    mime: str
    size_bytes: int


def _headers(user_id: str) -> dict[str, str]:
    settings = get_settings()
    return {
        "X-Internal-Token": settings.server.auth_token,
        "X-User-Id": user_id,
    }


async def _get(path: str, *, user_id: str) -> httpx.Response:
    settings = get_settings()
    url = f"{settings.server.api_base_url.rstrip('/')}{path}"
    timeout = min(settings.server.timeout_seconds, FILE_TIMEOUT_SECONDS)

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=_headers(user_id))
        except httpx.RequestError as e:
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            raise FileApiError("图片服务暂不可用") from e

        if response.status_code == 404:
            raise FileNotFound("图片不存在")
        if response.status_code >= 500 and attempt == 0:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue
        if response.status_code >= 400:
            raise FileApiError(f"图片服务返回 {response.status_code}")
        return response

    raise FileApiError("图片服务暂不可用")


async def get_file_metadata(user_id: str, file_id: str) -> FileMetadata:
    response = await _get(f"/internal/files/{file_id}", user_id=user_id)
    try:
        return FileMetadata.model_validate(response.json())
    except ValueError as e:
        raise FileApiError("图片服务返回了无效数据") from e


async def get_file_raw(user_id: str, file_id: str) -> tuple[bytes, str]:
    response = await _get(f"/internal/files/{file_id}/raw", user_id=user_id)
    mime = response.headers.get("content-type", "").split(";", 1)[0].strip()
    if not mime.startswith("image/"):
        raise FileApiError("图片服务返回了非图片内容")
    return response.content, mime
