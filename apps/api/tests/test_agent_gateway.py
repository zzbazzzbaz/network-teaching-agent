from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.gateway.agent import AgentGateway
from app.gateway.http_client import (
    UpstreamContractError,
    UpstreamUnavailable,
)

USER_ID = uuid.UUID("2f47c5d0-22d7-4d6e-8f3b-6c8e9f0a1b2c")
THREAD_ID = "8f14e45f-ceea-467a-9a2f-1d4c2b3a4e5f"
INTERNAL_TOKEN = "test-internal-token"


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        base_url="http://agent.test",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
        transport=httpx.MockTransport(handler),
    )


def _item(key: str) -> dict[str, Any]:
    return {
        "namespace": ["users", str(USER_ID), "memory"],
        "key": key,
        "value": {"content": key, "encoding": "utf-8"},
        "updated_at": "2026-10-28T10:00:00Z",
    }


def _gateway(handler: Callable[[httpx.Request], httpx.Response]) -> AgentGateway:
    return AgentGateway(_client(handler))


def _assert_internal_headers(request: httpx.Request) -> None:
    assert request.headers["X-Internal-Token"] == INTERNAL_TOKEN
    assert request.headers["X-User-Id"] == str(USER_ID)


def test_search_memory_paginates_and_uses_namespace_prefix() -> None:
    offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        body = json.loads(request.content)
        assert body["namespace_prefix"] == ["users", str(USER_ID), "memory"]
        assert body["limit"] == 100
        offsets.append(body["offset"])
        if body["offset"] == 0:
            return httpx.Response(
                200,
                json={"items": [_item(f"/{index}.md") for index in range(100)]},
            )
        return httpx.Response(200, json={"items": [_item("/last.md")]})

    items = _gateway(handler).search_memory(user_id=USER_ID)

    assert len(items) == 101
    assert offsets == [0, 100]
    assert items[-1].key == "/last.md"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"items": ["not-a-dict"]},
        {"items": [{"key": "/AGENTS.md", "value": {}}]},
    ],
)
def test_search_memory_rejects_contract_violations(payload: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        return httpx.Response(200, json=payload)

    with pytest.raises(UpstreamContractError):
        _gateway(handler).search_memory(user_id=USER_ID)


def test_get_memory_returns_none_for_json_null() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        assert request.url.params["namespace"] == f"users.{USER_ID}.memory"
        assert request.url.params["key"] == "/AGENTS.md"
        return httpx.Response(200, content=b"null")

    assert _gateway(handler).get_memory(user_id=USER_ID, key="/AGENTS.md") is None


def test_get_memory_sends_dot_joined_namespace_and_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        assert request.url.params["namespace"] == f"users.{USER_ID}.memory"
        assert request.url.params["key"] == "/AGENTS.md"
        return httpx.Response(200, json=_item("/AGENTS.md"))

    item = _gateway(handler).get_memory(user_id=USER_ID, key="/AGENTS.md")

    assert item is not None
    assert item.key == "/AGENTS.md"
    assert item.value["content"] == "/AGENTS.md"


def test_get_memory_rejects_contract_violation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        return httpx.Response(200, json={"key": "/AGENTS.md", "value": {}})

    with pytest.raises(UpstreamContractError):
        _gateway(handler).get_memory(user_id=USER_ID, key="/AGENTS.md")


def test_ensure_thread_posts_idempotent_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        assert request.method == "POST"
        assert request.url.path == "/threads"
        assert json.loads(request.content) == {
            "thread_id": THREAD_ID,
            "if_exists": "do_nothing",
        }
        return httpx.Response(200, json={"thread_id": THREAD_ID})

    _gateway(handler).ensure_thread(user_id=USER_ID, thread_id=THREAD_ID)


def test_delete_thread_accepts_204_and_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        assert request.method == "DELETE"
        assert request.url.path == f"/threads/{THREAD_ID}"
        return httpx.Response(204)

    _gateway(handler).delete_thread(user_id=USER_ID, thread_id=THREAD_ID)

    def missing_handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        return httpx.Response(404)

    _gateway(missing_handler).delete_thread(user_id=USER_ID, thread_id=THREAD_ID)


def test_delete_thread_raises_when_agent_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_internal_headers(request)
        return httpx.Response(500)

    with pytest.raises(UpstreamUnavailable):
        _gateway(handler).delete_thread(user_id=USER_ID, thread_id=THREAD_ID)
