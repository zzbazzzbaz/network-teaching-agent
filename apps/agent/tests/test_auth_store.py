from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest
from langgraph_sdk import Auth

import agent.core.auth as auth_module
from agent.core.auth import authenticate, scope_store

INTERNAL_TOKEN = "test-internal-token"
USER_ID = "2f47c5d0-22d7-4d6e-8f3b-6c8e9f0a1b2c"


def _internal_headers(**overrides: str) -> dict[bytes, bytes]:
    headers = {
        b"x-internal-token": INTERNAL_TOKEN.encode(),
        b"x-user-id": USER_ID.encode(),
    }
    for key, value in overrides.items():
        headers[key.encode()] = value.encode()
    return headers


def _ctx(action: str = "search") -> Auth.types.AuthContext:
    return cast(
        Auth.types.AuthContext,
        SimpleNamespace(
            user=SimpleNamespace(identity=USER_ID),
            action=action,
        ),
    )


@pytest.fixture(autouse=True)
def internal_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(server=SimpleNamespace(auth_token=INTERNAL_TOKEN)),
    )


def test_store_internal_token_authenticates_user() -> None:
    result = asyncio.run(
        authenticate(headers=_internal_headers(), path="/store/items/search")
    )
    assert result == {"identity": USER_ID}


def test_store_requires_internal_token_and_user() -> None:
    for headers, path in (
        ({}, "/store/items"),
        ({b"x-internal-token": INTERNAL_TOKEN.encode()}, "/store/items"),
        ({b"x-user-id": USER_ID.encode()}, "/store/items"),
        (_internal_headers(**{"x-internal-token": "wrong"}), "/store/items"),
        (_internal_headers(**{"x-user-id": "not-a-uuid"}), "/store/items"),
    ):
        with pytest.raises(Auth.exceptions.HTTPException) as error:
            asyncio.run(authenticate(headers=headers, path=path))
        assert error.value.status_code in {401, 403}


@pytest.mark.parametrize(
    "path",
    [
        "/threads",
        f"/threads/{USER_ID}",
    ],
)
def test_internal_token_can_authenticate_thread_lifecycle(path: str) -> None:
    result = asyncio.run(authenticate(headers=_internal_headers(), path=path))
    assert result == {"identity": USER_ID}


@pytest.mark.parametrize(
    "path",
    [
        "/threads/search",
        f"/threads/{USER_ID}/state",
        f"/threads/{USER_ID}/runs/stream",
        "/runs/stream",
        "/threads/not-a-uuid",
    ],
)
def test_internal_token_cannot_access_other_thread_paths(path: str) -> None:
    with pytest.raises(Auth.exceptions.HTTPException) as error:
        asyncio.run(authenticate(headers=_internal_headers(), path=path))
    assert error.value.status_code == 401


@pytest.mark.parametrize("path", ["/store/items", "/threads"])
def test_internal_paths_still_require_internal_token(path: str) -> None:
    with pytest.raises(Auth.exceptions.HTTPException) as error:
        asyncio.run(authenticate(headers={}, path=path))
    assert error.value.status_code == 401


def test_browser_jwt_cannot_access_store(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_verify(token: str) -> dict[str, str]:
        return {"sub": USER_ID}

    monkeypatch.setattr(auth_module, "_verify", fake_verify)

    with pytest.raises(Auth.exceptions.HTTPException) as error:
        asyncio.run(
            authenticate(
                headers={},
                path="/store/items",
                authorization="Bearer token",
            )
        )
    assert error.value.status_code == 401


def test_store_scope_allows_only_current_memory_namespace() -> None:
    value: dict[str, Any] = {
        "namespace": ("users", USER_ID, "memory"),
        "key": "/AGENTS.md",
    }
    asyncio.run(scope_store(_ctx("get"), value))
    assert value["namespace"] == ("users", USER_ID, "memory")

    search_value: dict[str, Any] = {"namespace": ["users", USER_ID, "memory"]}
    asyncio.run(scope_store(_ctx("search"), search_value))

    for namespace in (
        ("users", "other-user", "memory"),
        ("users", USER_ID),
        ("users", USER_ID, "memory", "extra"),
        (),
    ):
        with pytest.raises(Auth.exceptions.HTTPException) as error:
            asyncio.run(scope_store(_ctx("search"), {"namespace": namespace}))
        assert error.value.status_code == 403


def test_store_get_rejects_traversal_key() -> None:
    with pytest.raises(Auth.exceptions.HTTPException) as error:
        asyncio.run(
            scope_store(
                _ctx("get"),
                {
                    "namespace": ("users", USER_ID, "memory"),
                    "key": "/../AGENTS.md",
                },
            )
        )
    assert error.value.status_code == 403


def test_store_write_is_forbidden() -> None:
    for action, value in (
        (
            "put",
            {
                "namespace": ("users", USER_ID, "memory"),
                "key": "/AGENTS.md",
                "value": {},
            },
        ),
        (
            "delete",
            {
                "namespace": ("users", USER_ID, "memory"),
                "key": "/AGENTS.md",
            },
        ),
    ):
        with pytest.raises(Auth.exceptions.HTTPException) as error:
            asyncio.run(scope_store(_ctx(action), value))
        assert error.value.status_code == 403


def test_store_list_namespaces_is_forbidden() -> None:
    with pytest.raises(Auth.exceptions.HTTPException) as error:
        asyncio.run(
            scope_store(
                _ctx("list_namespaces"),
                {"namespace": ("users", USER_ID, "memory")},
            )
        )
    assert error.value.status_code == 403
