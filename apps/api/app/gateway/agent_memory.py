from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.core.config import Settings


class MemoryGatewayError(RuntimeError):
    """Agent Store 不可用或返回了非法响应。"""


def _namespace(user_id: uuid.UUID) -> list[str]:
    return ["users", str(user_id), "memory"]


def _headers(settings: Settings, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Internal-Token": settings.server.auth_token,
        "X-User-Id": str(user_id),
    }


def _request_json(
    settings: Settings,
    *,
    method: str,
    path: str,
    user_id: uuid.UUID,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> object:
    base_url = settings.server.agent_base_url.rstrip("/")
    try:
        response = httpx.request(
            method,
            f"{base_url}{path}",
            params=params,
            json=json,
            headers=_headers(settings, user_id),
            timeout=settings.server.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as e:
        raise MemoryGatewayError("Agent 记忆服务暂不可用") from e


def search_memory_items(
    settings: Settings,
    *,
    user_id: uuid.UUID,
) -> list[dict[str, Any]]:
    namespace = _namespace(user_id)
    items: list[dict[str, Any]] = []
    offset = 0
    page_size = 100
    while True:
        payload = _request_json(
            settings,
            method="POST",
            path="/store/items/search",
            user_id=user_id,
            json={
                "namespace_prefix": namespace,
                "limit": page_size,
                "offset": offset,
            },
        )
        page = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(page, list):
            raise MemoryGatewayError("Agent 记忆服务返回格式错误")
        for item in page:
            if not isinstance(item, dict):
                raise MemoryGatewayError("Agent 记忆服务返回格式错误")
            items.append(item)
        if len(page) < page_size:
            break
        offset += page_size
    return items


def get_memory_item(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    key: str,
) -> dict[str, Any] | None:
    payload = _request_json(
        settings,
        method="GET",
        path="/store/items",
        user_id=user_id,
        params={
            "namespace": ".".join(_namespace(user_id)),
            "key": key,
        },
    )
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise MemoryGatewayError("Agent 记忆服务返回格式错误")
    return payload
