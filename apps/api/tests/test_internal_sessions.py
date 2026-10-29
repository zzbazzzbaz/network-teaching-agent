from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.session import ChatSession
from app.models.user import Users

SESSIONS = "/api/v1/sessions"
INTERNAL_TITLE = "/internal/sessions/{session_id}/title"


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
    agent_id: str = "exp_agent",
) -> dict[str, Any]:
    response = client.post(
        SESSIONS,
        json={"title": title, "agent_id": agent_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _internal_headers(client: TestClient, user_id: uuid.UUID | str) -> dict[str, str]:
    settings = cast(FastAPI, client.app).state.settings
    return {
        "X-Internal-Token": settings.server.auth_token,
        "X-User-Id": str(user_id),
    }


def _title_source(client: TestClient, session_id: str) -> str:
    with cast(FastAPI, client.app).state.session_factory() as session:
        source = session.scalar(
            select(ChatSession.title_source).where(
                ChatSession.session_id == uuid.UUID(session_id)
            )
        )
    assert source is not None
    return source


def test_auto_title_updates_default_session(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login(client)
    created = _create(client, headers)

    response = client.post(
        INTERNAL_TITLE.format(session_id=created["session_id"]),
        json={"title": "TCP 三次握手"},
        headers=_internal_headers(client, user.user_id),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "updated": True,
        "title": "TCP 三次握手",
        "reason": "updated",
    }
    assert _title_source(client, created["session_id"]) == "auto"

    fetched = client.get(f"{SESSIONS}/{created['session_id']}", headers=headers)
    assert fetched.json()["title"] == "TCP 三次握手"


def test_auto_title_is_idempotent(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login(client)
    created = _create(client, headers)
    internal = _internal_headers(client, user.user_id)

    first = client.post(
        INTERNAL_TITLE.format(session_id=created["session_id"]),
        json={"title": "TCP 三次握手"},
        headers=internal,
    )
    assert first.status_code == 200

    second = client.post(
        INTERNAL_TITLE.format(session_id=created["session_id"]),
        json={"title": "另一个标题"},
        headers=internal,
    )

    assert second.status_code == 200, second.text
    assert second.json() == {
        "updated": False,
        "title": "TCP 三次握手",
        "reason": "not_default",
    }
    fetched = client.get(f"{SESSIONS}/{created['session_id']}", headers=headers)
    assert fetched.json()["title"] == "TCP 三次握手"


def test_auto_title_does_not_overwrite_user_title(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login(client)
    created = _create(client, headers)

    renamed = client.patch(
        f"{SESSIONS}/{created['session_id']}",
        json={"title": "手动标题"},
        headers=headers,
    )
    assert renamed.status_code == 200

    response = client.post(
        INTERNAL_TITLE.format(session_id=created["session_id"]),
        json={"title": "自动标题"},
        headers=_internal_headers(client, user.user_id),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "updated": False,
        "title": "手动标题",
        "reason": "not_default",
    }
    assert _title_source(client, created["session_id"]) == "user"


def test_create_with_title_sets_user_source(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)
    created = _create(client, headers, "学习 TCP")

    assert _title_source(client, created["session_id"]) == "user"


def test_create_without_title_sets_default_source(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)
    created = _create(client, headers, "   ")

    assert created["title"] == "新会话"
    assert _title_source(client, created["session_id"]) == "default"


def test_rename_sets_user_source(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)
    created = _create(client, headers)
    assert _title_source(client, created["session_id"]) == "default"

    response = client.patch(
        f"{SESSIONS}/{created['session_id']}",
        json={"title": "手动标题"},
        headers=headers,
    )
    assert response.status_code == 200
    assert _title_source(client, created["session_id"]) == "user"


def test_auto_title_requires_internal_token(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login(client)
    created = _create(client, headers)

    assert (
        client.post(
            INTERNAL_TITLE.format(session_id=created["session_id"]),
            json={"title": "标题"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            INTERNAL_TITLE.format(session_id=created["session_id"]),
            json={"title": "标题"},
            headers={
                "X-Internal-Token": "wrong-token",
                "X-User-Id": str(user.user_id),
            },
        ).status_code
        == 403
    )


def test_auto_title_requires_owner(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user("alice", "password123")
    bob = create_user("bob", "password456")
    alice_headers = _login(client, "alice", "password123")
    created = _create(client, alice_headers)

    response = client.post(
        INTERNAL_TITLE.format(session_id=created["session_id"]),
        json={"title": "篡改标题"},
        headers=_internal_headers(client, bob.user_id),
    )

    assert response.status_code == 404


def test_auto_title_rejects_empty_title(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login(client)
    created = _create(client, headers)

    response = client.post(
        INTERNAL_TITLE.format(session_id=created["session_id"]),
        json={"title": "   "},
        headers=_internal_headers(client, user.user_id),
    )

    assert response.status_code == 422
    assert _title_source(client, created["session_id"]) == "default"


def test_auto_title_truncates_long_title(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login(client)
    created = _create(client, headers)

    response = client.post(
        INTERNAL_TITLE.format(session_id=created["session_id"]),
        json={"title": "x" * 40},
        headers=_internal_headers(client, user.user_id),
    )

    assert response.status_code == 200, response.text
    assert response.json()["updated"] is True
    assert response.json()["title"] == "x" * 24

    fetched = client.get(f"{SESSIONS}/{created['session_id']}", headers=headers)
    assert fetched.json()["title"] == "x" * 24
