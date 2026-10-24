from collections.abc import Callable
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.user import Users
from app.models.user_sandbox import UserSandbox
from app.services import sandbox_service

SANDBOX = "/api/v1/sandbox"


class FakeSandbox:
    def __init__(self, sandbox_id: str) -> None:
        self.sandbox_id = sandbox_id
        self.killed = False
        self.timeout: int | None = None

    def get_host(self, port: int) -> str:
        assert port == 9000
        return f"9000-{self.sandbox_id}.example.test"

    def is_running(self) -> bool:
        return not self.killed

    def set_timeout(self, timeout: int) -> None:
        self.timeout = timeout

    def kill(self) -> None:
        self.killed = True


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


def test_sandbox_requires_auth(client: TestClient) -> None:
    assert client.get(SANDBOX).status_code == 401
    assert client.post(SANDBOX).status_code == 401
    assert client.delete(SANDBOX).status_code == 401


def test_sandbox_lifecycle(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user()
    headers = _login(client)

    assert client.get(SANDBOX, headers=headers).status_code == 404

    sandboxes: list[FakeSandbox] = []

    def create(_settings: object, *, user_id: str) -> FakeSandbox:
        sandbox = FakeSandbox(f"sbx-{len(sandboxes) + 1}")
        sandboxes.append(sandbox)
        return sandbox

    def connect(_settings: object, sandbox_id: str) -> FakeSandbox:
        return next(item for item in sandboxes if item.sandbox_id == sandbox_id)

    monkeypatch.setattr(sandbox_service, "create_sandbox", create)
    monkeypatch.setattr(sandbox_service, "connect_sandbox", connect)

    created = client.post(SANDBOX, headers=headers)
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["sandbox_id"] == "sbx-1"
    assert payload["status"] == "running"
    assert payload["vscode_url"] == (
        "https://9000-sbx-1.example.test/vscode/"
    )
    assert payload["ttyd_url"] == "https://9000-sbx-1.example.test/ttyd/"

    reused = client.post(SANDBOX, headers=headers)
    assert reused.status_code == 200
    assert reused.json()["sandbox_id"] == "sbx-1"
    assert len(sandboxes) == 1
    assert sandboxes[0].timeout is not None

    fetched = client.get(SANDBOX, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["sandbox_id"] == "sbx-1"

    with cast(FastAPI, client.app).state.session_factory() as session:
        record = session.get(UserSandbox, user.user_id)
        assert record is not None
        assert record.sandbox_id == "sbx-1"

    deleted = client.delete(SANDBOX, headers=headers)
    assert deleted.status_code == 204
    assert sandboxes[0].killed is True
    assert client.get(SANDBOX, headers=headers).status_code == 404
    assert client.delete(SANDBOX, headers=headers).status_code == 204


def test_sandbox_is_isolated_by_user(
    client: TestClient,
    create_user: Callable[..., Users],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login(client, "alice", "password123")
    bob = _login(client, "bob", "password456")

    sandboxes: list[FakeSandbox] = []

    def create(_settings: object, *, user_id: str) -> FakeSandbox:
        sandbox = FakeSandbox(f"sbx-{len(sandboxes) + 1}")
        sandboxes.append(sandbox)
        return sandbox

    def connect(_settings: object, sandbox_id: str) -> FakeSandbox:
        return next(item for item in sandboxes if item.sandbox_id == sandbox_id)

    monkeypatch.setattr(sandbox_service, "create_sandbox", create)
    monkeypatch.setattr(sandbox_service, "connect_sandbox", connect)

    alice_sandbox = client.post(SANDBOX, headers=alice)
    assert alice_sandbox.status_code == 200
    assert alice_sandbox.json()["sandbox_id"] == "sbx-1"

    assert client.get(SANDBOX, headers=bob).status_code == 404
    bob_sandbox = client.post(SANDBOX, headers=bob)
    assert bob_sandbox.status_code == 200
    assert bob_sandbox.json()["sandbox_id"] == "sbx-2"

    assert client.get(SANDBOX, headers=alice).json()["sandbox_id"] == "sbx-1"
    assert client.get(SANDBOX, headers=bob).json()["sandbox_id"] == "sbx-2"
