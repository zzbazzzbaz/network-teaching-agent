from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.services.memory_service as memory_service_module
from app.core.config import Settings
from app.gateway.agent_memory import MemoryGatewayError
from app.models.user import Users

TREE = "/api/v1/memory/tree"
FILE = "/api/v1/memory/file"


def _login(
    client: TestClient,
    username: str = "alice",
    password: str = "password123",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _item(
    key: str,
    content: str | list[str] = "内容",
    *,
    encoding: str = "utf-8",
    updated_at: str = "2026-10-28T10:00:00Z",
) -> dict[str, Any]:
    return {
        "key": key,
        "value": {"content": content, "encoding": encoding},
        "updated_at": updated_at,
    }


def test_memory_tree_builds_directories_and_uses_current_user(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user()
    headers = _login(client)
    calls: list[uuid.UUID] = []

    def fake_search(
        settings: Settings,
        *,
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        calls.append(user_id)
        return [
            _item("/AGENTS.md", "# 学生画像"),
            _item("/lab/learning.md", "实验记录"),
        ]

    monkeypatch.setattr(memory_service_module, "search_memory_items", fake_search)

    response = client.get(TREE, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert calls == [user.user_id]
    assert body["entries"] == [
        {
            "path": "/memory/AGENTS.md",
            "name": "AGENTS.md",
            "kind": "file",
            "size": len("# 学生画像".encode()),
            "modified_at": "2026-10-28T10:00:00Z",
        },
        {
            "path": "/memory/lab/",
            "name": "lab",
            "kind": "directory",
            "size": 0,
            "modified_at": None,
        },
        {
            "path": "/memory/lab/learning.md",
            "name": "learning.md",
            "kind": "file",
            "size": len("实验记录".encode()),
            "modified_at": "2026-10-28T10:00:00Z",
        },
    ]


def test_memory_tree_empty(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user()
    headers = _login(client)
    monkeypatch.setattr(
        memory_service_module,
        "search_memory_items",
        lambda settings, *, user_id: [],
    )

    response = client.get(TREE, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"entries": []}


def test_memory_file_uses_store_relative_key(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user()
    headers = _login(client)
    calls: list[str] = []

    def fake_get(
        settings: Settings,
        *,
        user_id: uuid.UUID,
        key: str,
    ) -> dict[str, Any] | None:
        calls.append(key)
        return _item("/AGENTS.md", "# 学生画像")

    monkeypatch.setattr(memory_service_module, "get_memory_item", fake_get)

    response = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert calls == ["/AGENTS.md"]
    assert response.json()["path"] == "/memory/AGENTS.md"
    assert response.json()["content"] == "# 学生画像"
    assert response.json()["size"] == len("# 学生画像".encode())


def test_memory_file_rejects_invalid_paths(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user()
    headers = _login(client)

    def fake_get(
        settings: Settings,
        *,
        user_id: uuid.UUID,
        key: str,
    ) -> dict[str, Any] | None:
        raise AssertionError("非法路径不应访问 Agent")

    monkeypatch.setattr(memory_service_module, "get_memory_item", fake_get)

    for path in (
        "/etc/passwd",
        "/memory/",
        "/memory/../AGENTS.md",
        "/memory/%2e%2e/AGENTS.md",
        "/memory/lab\\AGENTS.md",
        "/memory//AGENTS.md",
    ):
        response = client.get(FILE, params={"path": path}, headers=headers)
        assert response.status_code == 422, (path, response.text)


def test_memory_file_rejects_binary_and_large_files(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user()
    headers = _login(client)
    item: dict[str, Any] | None = None

    def fake_get(
        settings: Settings,
        *,
        user_id: uuid.UUID,
        key: str,
    ) -> dict[str, Any] | None:
        return item

    monkeypatch.setattr(memory_service_module, "get_memory_item", fake_get)

    item = _item("/AGENTS.md", "AAEC", encoding="base64")
    binary = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert binary.status_code == 415

    item = _item("/AGENTS.md", "x" * (128 * 1024 + 1))
    large = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert large.status_code == 413


def test_memory_file_not_found(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user()
    headers = _login(client)
    monkeypatch.setattr(
        memory_service_module,
        "get_memory_item",
        lambda settings, *, user_id, key: None,
    )

    response = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert response.status_code == 404


def test_memory_agent_unavailable(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user()
    headers = _login(client)

    def fail(settings: Settings, *, user_id: uuid.UUID) -> list[dict[str, Any]]:
        raise MemoryGatewayError("down")

    monkeypatch.setattr(memory_service_module, "search_memory_items", fail)

    response = client.get(TREE, headers=headers)
    assert response.status_code == 503


def test_memory_has_no_write_endpoint(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)

    assert client.post(TREE, headers=headers).status_code == 405
    assert client.delete(TREE, headers=headers).status_code == 405
