from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.models.user import Users

SESSIONS = "/api/v1/sessions"


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
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create(
    client: TestClient,
    headers: dict[str, str],
    title: str = "",
) -> dict[str, Any]:
    response = client.post(SESSIONS, json={"title": title}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_sessions_require_auth(client: TestClient) -> None:
    assert client.get(SESSIONS).status_code == 401
    assert client.post(SESSIONS, json={}).status_code == 401


def test_session_lifecycle(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    headers = _login(client)

    created = _create(client, headers, "  TCP 入门  ")
    assert created["title"] == "TCP 入门"
    session_id = created["session_id"]

    listed = client.get(SESSIONS, headers=headers)
    assert listed.status_code == 200
    assert [item["session_id"] for item in listed.json()] == [session_id]

    fetched = client.get(f"{SESSIONS}/{session_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "TCP 入门"

    renamed = client.patch(
        f"{SESSIONS}/{session_id}",
        json={"title": "三次握手"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "三次握手"

    touched = client.post(f"{SESSIONS}/{session_id}/touch", headers=headers)
    assert touched.status_code == 204

    deleted = client.delete(f"{SESSIONS}/{session_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"{SESSIONS}/{session_id}", headers=headers).status_code == 404


def test_default_session_title(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    headers = _login(client)
    created = _create(client, headers, "   ")
    assert created["title"] == "新会话"


def test_session_title_too_long(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    headers = _login(client)
    response = client.post(SESSIONS, json={"title": "x" * 101}, headers=headers)
    assert response.status_code == 400


def test_session_ownership(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login(client, "alice", "password123")
    bob = _login(client, "bob", "password456")

    created = _create(client, alice, "Alice 的会话")
    session_id = created["session_id"]

    assert client.get(SESSIONS, headers=bob).json() == []
    assert client.get(f"{SESSIONS}/{session_id}", headers=bob).status_code == 404
    assert (
        client.patch(
            f"{SESSIONS}/{session_id}",
            json={"title": "被篡改"},
            headers=bob,
        ).status_code
        == 404
    )
    assert client.post(f"{SESSIONS}/{session_id}/touch", headers=bob).status_code == 404
    assert client.delete(f"{SESSIONS}/{session_id}", headers=bob).status_code == 404

    assert client.get(f"{SESSIONS}/{session_id}", headers=alice).status_code == 200


def test_session_list_is_isolated_and_ordered(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login(client, "alice", "password123")
    bob = _login(client, "bob", "password456")

    first = _create(client, alice, "第一个")
    second = _create(client, alice, "第二个")
    _create(client, bob, "Bob 的会话")

    listed = client.get(SESSIONS, headers=alice).json()
    assert {item["session_id"] for item in listed} == {
        first["session_id"],
        second["session_id"],
    }

    # touch 第一个后，它应排到最前面
    assert client.post(f"{SESSIONS}/{first['session_id']}/touch", headers=alice).status_code == 204
    reordered = client.get(SESSIONS, headers=alice).json()
    assert reordered[0]["session_id"] == first["session_id"]
