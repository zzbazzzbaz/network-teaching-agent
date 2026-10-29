from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.gateway.agent import StoreItem
from app.gateway.http_client import UpstreamContractError
from app.models.user import Users
from tests.fakes import FakeAgentGateway

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
) -> StoreItem:
    return StoreItem(
        namespace=["users", "test", "memory"],
        key=key,
        value={"content": content, "encoding": encoding},
        updated_at=updated_at,
    )


def test_memory_tree_builds_directories_and_uses_current_user(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    user = create_user()
    headers = _login(client)
    fake_agent.items = [
        _item("/AGENTS.md", "# 学生画像"),
        _item("/lab/learning.md", "实验记录"),
    ]

    response = client.get(TREE, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert fake_agent.search_calls == [user.user_id]
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


def test_memory_tree_uses_value_modified_at_and_falls_back(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    create_user()
    headers = _login(client)
    fake_agent.items = [
        StoreItem(
            namespace=["users", "test", "memory"],
            key="/valid.md",
            value={
                "content": "valid",
                "modified_at": "2026-10-29T01:02:03Z",
            },
            updated_at="2026-10-28T10:00:00Z",
        ),
        StoreItem(
            namespace=["users", "test", "memory"],
            key="/invalid.md",
            value={
                "content": "invalid",
                "modified_at": "not-a-timestamp",
            },
            updated_at="2026-10-28T10:00:00Z",
        ),
    ]

    response = client.get(TREE, headers=headers)

    assert response.status_code == 200, response.text
    entries = {entry["path"]: entry for entry in response.json()["entries"]}
    assert entries["/memory/valid.md"]["modified_at"] == "2026-10-29T01:02:03Z"
    assert entries["/memory/invalid.md"]["modified_at"] == "2026-10-28T10:00:00Z"


def test_memory_tree_empty(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    create_user()
    headers = _login(client)

    response = client.get(TREE, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"entries": []}


def test_memory_file_uses_store_relative_key(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    user = create_user()
    headers = _login(client)
    fake_agent.item = _item("/AGENTS.md", "# 学生画像")

    response = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert fake_agent.get_calls == [(user.user_id, "/AGENTS.md")]
    assert response.json()["path"] == "/memory/AGENTS.md"
    assert response.json()["content"] == "# 学生画像"
    assert response.json()["size"] == len("# 学生画像".encode())


def test_memory_file_rejects_invalid_paths(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    create_user()
    headers = _login(client)

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
    assert fake_agent.get_calls == []


def test_memory_file_rejects_binary_and_large_files(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    create_user()
    headers = _login(client)

    fake_agent.item = _item("/AGENTS.md", "AAEC", encoding="base64")
    binary = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert binary.status_code == 415

    fake_agent.item = _item("/AGENTS.md", "x" * (128 * 1024 + 1))
    large = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert large.status_code == 413


def test_memory_file_missing_content_is_unsupported_media_type(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    create_user()
    headers = _login(client)
    fake_agent.item = StoreItem(
        namespace=["users", "test", "memory"],
        key="/AGENTS.md",
        value={"encoding": "utf-8"},
    )

    response = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert response.status_code == 415


def test_memory_file_not_found(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    user = create_user()
    headers = _login(client)

    response = client.get(
        FILE,
        params={"path": "/memory/AGENTS.md"},
        headers=headers,
    )
    assert response.status_code == 404
    assert fake_agent.get_calls == [
        (user.user_id, "/AGENTS.md"),
        (user.user_id, "/memory/AGENTS.md"),
    ]


def test_memory_agent_unavailable(
    client: TestClient,
    create_user: Callable[..., Users],
    fake_agent: FakeAgentGateway,
) -> None:
    create_user()
    headers = _login(client)
    fake_agent.fail = UpstreamContractError("bad contract")

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
