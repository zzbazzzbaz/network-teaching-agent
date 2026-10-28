from __future__ import annotations

import uuid
from pathlib import PurePosixPath
from typing import Any

from app.api.schemas.memory import (
    MemoryEntry,
    MemoryFileResponse,
    MemoryTreeResponse,
)
from app.core.config import Settings
from app.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
    ServiceUnavailableError,
    UnprocessableError,
    UnsupportedMediaTypeError,
)
from app.gateway.agent_memory import (
    MemoryGatewayError,
    get_memory_item,
    search_memory_items,
)

MEMORY_PREFIX = "/memory/"
MAX_MEMORY_FILE_BYTES = 128 * 1024
MAX_MEMORY_PATH_LENGTH = 1024


def _validate_memory_path(path: str) -> None:
    if not path.startswith(MEMORY_PREFIX) or path == MEMORY_PREFIX:
        raise UnprocessableError("path 必须位于 /memory/ 下")
    if len(path) > MAX_MEMORY_PATH_LENGTH:
        raise UnprocessableError("path 过长")
    if path.endswith("/"):
        raise UnprocessableError("path 必须指向文件")
    if "\\" in path or "\x00" in path or "%" in path:
        raise UnprocessableError("path 包含非法字符")
    if any(ord(char) < 32 or ord(char) == 127 for char in path):
        raise UnprocessableError("path 包含非法字符")
    components = path.split("/")
    if any(component in {"", ".", ".."} for component in components[2:]):
        raise UnprocessableError("path 包含非法路径片段")


def _path_from_store_key(key: str) -> str | None:
    """把 StoreBackend 的 key 还原成浏览器使用的 /memory/ 路径。

    CompositeBackend 会把 ``/memory/lab/x.md`` 去掉前缀后存成 ``/lab/x.md``；
    同时兼容直接以 ``/memory/`` 开头的 key。
    """
    if not key or key == "/":
        return None
    if key == "/memory" or key.startswith(MEMORY_PREFIX):
        path = key
    else:
        path = f"/memory{key if key.startswith('/') else '/' + key}"
    if path == "/memory/" or path.endswith("/"):
        return None
    return path


def _file_value(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("value")
    if not isinstance(value, dict):
        raise UnsupportedMediaTypeError("记忆文件不是文本文件")
    return value


def _text_content(value: dict[str, Any]) -> str:
    encoding = value.get("encoding", "utf-8")
    if not isinstance(encoding, str) or encoding.lower() != "utf-8":
        raise UnsupportedMediaTypeError("记忆文件不是 UTF-8 文本")
    content = value.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list) and all(isinstance(line, str) for line in content):
        return "\n".join(content)
    raise UnsupportedMediaTypeError("记忆文件不是 UTF-8 文本")


def _content_size(value: dict[str, Any]) -> int:
    try:
        return len(_text_content(value).encode("utf-8"))
    except UnsupportedMediaTypeError:
        return 0


def _safe_content_size(item: dict[str, Any]) -> int:
    try:
        value = _file_value(item)
    except UnsupportedMediaTypeError:
        return 0
    return _content_size(value)


def _modified_at(item: dict[str, Any]) -> str | None:
    value = item.get("value")
    if isinstance(value, dict):
        modified_at = value.get("modified_at")
        if isinstance(modified_at, str) and modified_at:
            return modified_at
    updated_at = item.get("updated_at")
    if isinstance(updated_at, str) and updated_at:
        return updated_at
    return None


def _directories_for(path: str) -> set[str]:
    parts = path[len(MEMORY_PREFIX) :].split("/")
    return {
        f"/memory/{'/'.join(parts[:index])}/"
        for index in range(1, len(parts))
    }


class MemoryService:
    def get_tree(
        self,
        *,
        user_id: uuid.UUID,
        settings: Settings,
    ) -> MemoryTreeResponse:
        try:
            items = search_memory_items(settings, user_id=user_id)
        except MemoryGatewayError as e:
            raise ServiceUnavailableError("记忆服务暂不可用") from e

        files: dict[str, dict[str, Any]] = {}
        directories: set[str] = set()
        for item in items:
            key = item.get("key")
            if not isinstance(key, str):
                continue
            path = _path_from_store_key(key)
            if path is None:
                continue
            try:
                _validate_memory_path(path)
            except UnprocessableError:
                continue
            files.setdefault(path, item)
            directories.update(_directories_for(path))

        entries = [
            MemoryEntry(
                path=path,
                name=PurePosixPath(path).name,
                kind="file",
                size=_safe_content_size(item),
                modified_at=_modified_at(item),
            )
            for path, item in files.items()
        ]
        entries.extend(
            MemoryEntry(
                path=path,
                name=PurePosixPath(path.rstrip("/")).name,
                kind="directory",
                size=0,
                modified_at=None,
            )
            for path in directories
        )
        entries.sort(key=lambda entry: entry.path)
        return MemoryTreeResponse(entries=entries)

    def get_file(
        self,
        *,
        user_id: uuid.UUID,
        path: str,
        settings: Settings,
    ) -> MemoryFileResponse:
        _validate_memory_path(path)
        store_key = path[len("/memory") :]

        try:
            item = get_memory_item(settings, user_id=user_id, key=store_key)
            if item is None and store_key != path:
                item = get_memory_item(settings, user_id=user_id, key=path)
        except MemoryGatewayError as e:
            raise ServiceUnavailableError("记忆服务暂不可用") from e

        if item is None:
            raise NotFoundError("记忆文件不存在")

        value = _file_value(item)
        content = _text_content(value)
        size = len(content.encode("utf-8"))
        if size > MAX_MEMORY_FILE_BYTES:
            raise PayloadTooLargeError("记忆文件超过 128 KiB")

        return MemoryFileResponse(
            path=path,
            name=PurePosixPath(path).name,
            size=size,
            modified_at=_modified_at(item),
            content=content,
        )


memory_service = MemoryService()
