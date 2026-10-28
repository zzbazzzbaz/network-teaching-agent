from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
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
    agent_id: str = "exp_agent",
) -> dict[str, Any]:
    response = client.post(
        SESSIONS,
        json={"title": title, "agent_id": agent_id},
        headers=headers,
    )
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
    assert created["agent_id"] == "exp_agent"
    session_id = created["session_id"]

    listed = client.get(SESSIONS, headers=headers)
    assert listed.status_code == 200
    assert [item["session_id"] for item in listed.json()["items"]] == [session_id]
    assert listed.json()["total"] == 1

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
    response = client.post(
        SESSIONS,
        json={"title": "x" * 101, "agent_id": "exp_agent"},
        headers=headers,
    )
    assert response.status_code == 422


def test_session_agent_id_is_required_and_validated(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    create_user()
    headers = _login(client)

    missing = client.post(SESSIONS, json={"title": "学习"}, headers=headers)
    assert missing.status_code == 422

    invalid = client.post(
        SESSIONS,
        json={"title": "学习", "agent_id": "other_agent"},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_session_can_filter_by_agent(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    create_user()
    headers = _login(client)

    exp = _create(client, headers, "实验", agent_id="exp_agent")
    teach = _create(client, headers, "学习", agent_id="teach_agent")

    all_sessions = client.get(SESSIONS, headers=headers)
    assert {item["session_id"] for item in all_sessions.json()["items"]} == {
        exp["session_id"],
        teach["session_id"],
    }

    exp_sessions = client.get(SESSIONS, params={"agent_id": "exp_agent"}, headers=headers)
    assert [item["session_id"] for item in exp_sessions.json()["items"]] == [exp["session_id"]]

    teach_sessions = client.get(SESSIONS, params={"agent_id": "teach_agent"}, headers=headers)
    assert [item["session_id"] for item in teach_sessions.json()["items"]] == [teach["session_id"]]


def test_session_agent_id_cannot_be_patched(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    create_user()
    headers = _login(client)
    created = _create(client, headers, "学习", agent_id="teach_agent")

    response = client.patch(
        f"{SESSIONS}/{created['session_id']}",
        json={"title": "改名", "agent_id": "exp_agent"},
        headers=headers,
    )
    assert response.status_code == 422

    fetched = client.get(f"{SESSIONS}/{created['session_id']}", headers=headers)
    assert fetched.json()["agent_id"] == "teach_agent"
    assert fetched.json()["title"] == "学习"


def test_session_ownership(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login(client, "alice", "password123")
    bob = _login(client, "bob", "password456")

    created = _create(client, alice, "Alice 的会话")
    session_id = created["session_id"]

    assert client.get(SESSIONS, headers=bob).json()["items"] == []
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


def test_session_list_is_isolated_and_ordered(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login(client, "alice", "password123")
    bob = _login(client, "bob", "password456")

    first = _create(client, alice, "第一个")
    second = _create(client, alice, "第二个")
    _create(client, bob, "Bob 的会话")

    listed = client.get(SESSIONS, headers=alice).json()["items"]
    assert {item["session_id"] for item in listed} == {
        first["session_id"],
        second["session_id"],
    }

    # touch 第一个后，它应排到最前面
    assert client.post(f"{SESSIONS}/{first['session_id']}/touch", headers=alice).status_code == 204
    reordered = client.get(SESSIONS, headers=alice).json()["items"]
    assert reordered[0]["session_id"] == first["session_id"]


def test_session_agent_migration_backfills_existing_sessions(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from app.core.config import get_settings

    monkeypatch.setenv("DB_DATABASE_URL", database_url)
    monkeypatch.setenv("SERVER_AGENT_BASE_URL", "http://127.0.0.1:2024")
    monkeypatch.setenv("SERVER_TIMEOUT_SECONDS", "15")
    get_settings.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))

    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    try:
        command.upgrade(config, "0004_question_bank")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users
                        (user_id, username, password_hash, status)
                    VALUES
                        (:user_id, :username, :password_hash, true)
                    """
                ),
                {
                    "user_id": user_id,
                    "username": "legacy-session-user",
                    "password_hash": "hash",
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO sessions (session_id, user_id, title)
                    VALUES (:session_id, :user_id, :title)
                    """
                ),
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "title": "旧会话",
                },
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT agent_id
                    FROM sessions
                    WHERE session_id = :session_id
                    """
                ),
                {"session_id": session_id},
            ).one()
        assert row.agent_id == "exp_agent"
    finally:
        get_settings.cache_clear()


def test_session_list_pagination(
    client: TestClient, create_user: Callable[..., Users]
) -> None:
    create_user()
    headers = _login(client)
    for index in range(3):
        _create(client, headers, f"会话 {index}")

    first = client.get(SESSIONS, params={"limit": 2}, headers=headers)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["total"] == 3
    assert first_body["limit"] == 2
    assert first_body["offset"] == 0
    assert len(first_body["items"]) == 2

    second = client.get(
        SESSIONS,
        params={"limit": 2, "offset": 2},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["total"] == 3
    assert len(second.json()["items"]) == 1

    invalid = client.get(SESSIONS, params={"limit": 0}, headers=headers)
    assert invalid.status_code == 422
    too_large = client.get(SESSIONS, params={"limit": 51}, headers=headers)
    assert too_large.status_code == 422


def test_openapi_generation(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/sessions" in paths
    assert "/api/v1/question-bank/questions" in paths
    assert "/api/v1/memory/file" in paths
