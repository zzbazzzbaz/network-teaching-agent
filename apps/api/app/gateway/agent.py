"""Agent 端网关：Store 读取和 thread 生命周期。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.gateway.http_client import (
    UpstreamContractError,
    UpstreamStatusError,
    request_json,
)

PAGE_SIZE = 100
MAX_ITEMS = 5_000


def _memory_namespace(user_id: uuid.UUID) -> list[str]:
    return ["users", str(user_id), "memory"]


class StoreItem(BaseModel):
    """LangGraph Store 的单条记录。"""

    model_config = ConfigDict(extra="ignore")

    namespace: list[str]
    key: str
    value: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StoreSearchResponse(BaseModel):
    """POST /store/items/search 的响应。"""

    model_config = ConfigDict(extra="ignore")

    items: list[StoreItem]


class MemoryFileValue(BaseModel):
    """deepagents StoreBackend 的文件 value 结构。"""

    model_config = ConfigDict(extra="ignore")

    content: str | list[str]
    encoding: str = "utf-8"
    # 传输层保持 ISO 字符串，service 解析成 datetime；
    # 非法时间戳不应导致整个文件不可读。
    modified_at: str | None = None


class AgentGateway:
    """Agent 内部接口的唯一入口。"""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    @staticmethod
    def _headers(user_id: uuid.UUID) -> dict[str, str]:
        return {"X-User-Id": str(user_id)}

    def search_memory(self, *, user_id: uuid.UUID) -> list[StoreItem]:
        items: list[StoreItem] = []
        offset = 0
        while True:
            payload = request_json(
                self._http,
                method="POST",
                path="/store/items/search",
                headers=self._headers(user_id),
                json={
                    "namespace_prefix": _memory_namespace(user_id),
                    "limit": PAGE_SIZE,
                    "offset": offset,
                },
            )
            try:
                page = StoreSearchResponse.model_validate(payload)
            except ValidationError as e:
                raise UpstreamContractError("Agent Store 搜索响应格式错误") from e
            items.extend(page.items)
            if len(page.items) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            if len(items) > MAX_ITEMS:
                raise UpstreamContractError("Agent Store 返回条目过多")
        return items

    def get_memory(self, *, user_id: uuid.UUID, key: str) -> StoreItem | None:
        payload = request_json(
            self._http,
            method="GET",
            path="/store/items",
            headers=self._headers(user_id),
            params={
                "namespace": ".".join(_memory_namespace(user_id)),
                "key": key,
            },
        )
        if payload is None:
            return None
        try:
            return StoreItem.model_validate(payload)
        except ValidationError as e:
            raise UpstreamContractError("Agent Store 条目格式错误") from e

    def ensure_thread(self, *, user_id: uuid.UUID, thread_id: str) -> None:
        request_json(
            self._http,
            method="POST",
            path="/threads",
            headers=self._headers(user_id),
            json={"thread_id": thread_id, "if_exists": "do_nothing"},
        )

    def delete_thread(self, *, user_id: uuid.UUID, thread_id: str) -> None:
        try:
            request_json(
                self._http,
                method="DELETE",
                path=f"/threads/{thread_id}",
                headers=self._headers(user_id),
            )
        except UpstreamStatusError as e:
            if e.status_code == 404:
                return
            raise
