from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from e2b import SandboxException, SandboxNotFoundException
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models.user import Users
from app.models.user_sandbox import UserSandbox
from app.services import sandbox_reaper, sandbox_service

SANDBOX = "/api/v1/sandbox"
INTERNAL_SANDBOX = "/internal/sandbox/ensure"


class FakeSandbox:
    def __init__(self, sandbox_id: str) -> None:
        self.sandbox_id = sandbox_id
        self.killed = False
        self.paused = False
        self.already_paused = False
        self.timeout: int | None = None
        self.pause_calls = 0
        self.fail_pause = False

    def get_host(self, port: int) -> str:
        assert port == 9000
        return f"9000-{self.sandbox_id}.example.test"

    def is_running(self) -> bool:
        return not self.killed

    def pause(self) -> bool:
        if self.fail_pause:
            raise SandboxException("pause failed")
        self.pause_calls += 1
        if self.already_paused:
            return False
        self.paused = True
        return True

    def kill(self) -> None:
        self.killed = True
        self.paused = False


class FakeWorld:
    def __init__(self) -> None:
        self.sandboxes: list[FakeSandbox] = []
        self.missing: set[str] = set()
        self.connect_calls = 0
        self.kill_fail = False
        self.create_fail = False
        self.connect_fail = False

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sandbox_service, "create_sandbox", self.create)
        monkeypatch.setattr(sandbox_service, "connect_sandbox", self.connect)
        monkeypatch.setattr(sandbox_service, "pause_sandbox", self.pause)
        monkeypatch.setattr(sandbox_service, "kill_sandbox", self.kill)

    def create(self, _settings: object, *, user_id: str) -> FakeSandbox:
        assert user_id
        if self.create_fail:
            raise SandboxException("create failed")
        sandbox = FakeSandbox(f"sbx-{len(self.sandboxes) + 1}")
        self.sandboxes.append(sandbox)
        return sandbox

    def connect(
        self,
        _settings: object,
        sandbox_id: str,
        *,
        timeout: int | None = None,
    ) -> FakeSandbox:
        self.connect_calls += 1
        if self.connect_fail:
            raise SandboxException("connect failed")
        sandbox = self.find(sandbox_id)
        if timeout is not None:
            sandbox.timeout = timeout
        return sandbox

    def pause(self, _settings: object, sandbox_id: str) -> bool:
        return self.find(sandbox_id).pause()

    def kill(self, _settings: object, sandbox_id: str) -> bool:
        if self.kill_fail:
            raise SandboxException("kill failed")
        sandbox = self.find(sandbox_id)
        sandbox.kill()
        return True

    def find(self, sandbox_id: str) -> FakeSandbox:
        if sandbox_id in self.missing:
            raise SandboxNotFoundException("sandbox not found")
        for sandbox in self.sandboxes:
            if sandbox.sandbox_id == sandbox_id:
                return sandbox
        raise SandboxNotFoundException("sandbox not found")


@pytest.fixture
def world(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> FakeWorld:
    fake = FakeWorld()
    fake.install(monkeypatch)
    return fake


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


def _session_factory(client: TestClient) -> sessionmaker[Session]:
    return cast(FastAPI, client.app).state.session_factory


def _get_record(client: TestClient, user_id: UUID) -> UserSandbox | None:
    with _session_factory(client)() as session:
        return session.get(UserSandbox, user_id)


def _update_record(client: TestClient, user_id: UUID, **values: object) -> None:
    with _session_factory(client)() as session:
        record = session.get(UserSandbox, user_id)
        assert record is not None
        for key, value in values.items():
            setattr(record, key, value)
        session.commit()


def _settings(client: TestClient) -> Settings:
    return cast(FastAPI, client.app).state.settings


def _internal_headers(client: TestClient) -> dict[str, str]:
    return {"X-Internal-Token": _settings(client).agent_internal_token}


def _host(client: TestClient, sandbox_id: str) -> str:
    return f"9000-{sandbox_id}.{_settings(client).e2b.domain}"


def test_sandbox_requires_auth(client: TestClient) -> None:
    assert client.get(SANDBOX).status_code == 401
    assert client.post(SANDBOX).status_code == 401
    assert client.post(f"{SANDBOX}/heartbeat").status_code == 401
    assert client.post(f"{SANDBOX}/pause").status_code == 401
    assert client.delete(SANDBOX).status_code == 401


def test_sandbox_lifecycle(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)

    assert client.get(SANDBOX, headers=headers).status_code == 404

    created = client.post(SANDBOX, headers=headers)
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["sandbox_id"] == "sbx-1"
    assert payload["status"] == "running"
    assert payload["vscode_url"] == f"https://{_host(client, 'sbx-1')}/vscode/"
    assert payload["ttyd_url"] == f"https://{_host(client, 'sbx-1')}/ttyd/"
    assert payload["paused_at"] is None
    assert payload["hard_destroy_at"] > payload["last_active_at"]
    assert payload["heartbeat_seconds"] == _settings(client).ags.sandbox_heartbeat_seconds

    reused = client.post(SANDBOX, headers=headers)
    assert reused.status_code == 200
    assert reused.json()["sandbox_id"] == "sbx-1"
    assert len(world.sandboxes) == 1
    assert world.sandboxes[0].timeout is not None

    connect_calls = world.connect_calls
    fetched = client.get(SANDBOX, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["sandbox_id"] == "sbx-1"
    assert world.connect_calls == connect_calls

    with cast(FastAPI, client.app).state.session_factory() as session:
        record = session.get(UserSandbox, user.user_id)
        assert record is not None
        assert record.sandbox_id == "sbx-1"
        assert record.status == "running"

    deleted = client.delete(SANDBOX, headers=headers)
    assert deleted.status_code == 204
    assert world.sandboxes[0].killed is True
    assert client.get(SANDBOX, headers=headers).status_code == 404
    assert client.delete(SANDBOX, headers=headers).status_code == 204


def test_post_when_sandbox_missing_recreates(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    created = client.post(SANDBOX, headers=headers)
    assert created.status_code == 200
    assert created.json()["sandbox_id"] == "sbx-1"

    world.missing.add("sbx-1")

    recreated = client.post(SANDBOX, headers=headers)
    assert recreated.status_code == 200, recreated.text
    assert recreated.json()["sandbox_id"] == "sbx-2"

    record = _get_record(client, user.user_id)
    assert record is not None
    assert record.sandbox_id == "sbx-2"


def test_sandbox_create_failure_returns_503(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    create_user()
    headers = _login(client)
    world.create_fail = True

    response = client.post(SANDBOX, headers=headers)
    assert response.status_code == 503
    assert client.get(SANDBOX, headers=headers).status_code == 404


def test_heartbeat_and_pause_without_sandbox_return_404(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login(client)

    assert client.post(f"{SANDBOX}/heartbeat", headers=headers).status_code == 404
    assert client.post(f"{SANDBOX}/pause", headers=headers).status_code == 404


def test_heartbeat_missing_sandbox_clears_record(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    world.sandboxes.clear()

    response = client.post(f"{SANDBOX}/heartbeat", headers=headers)
    assert response.status_code == 404
    assert _get_record(client, user.user_id) is None
    assert client.get(SANDBOX, headers=headers).status_code == 404


def test_pause_failure_keeps_running(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    world.sandboxes[0].fail_pause = True
    response = client.post(f"{SANDBOX}/pause", headers=headers)
    assert response.status_code == 503

    record = _get_record(client, user.user_id)
    assert record is not None
    assert record.status == "running"
    fetched = client.get(SANDBOX, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "running"
    assert fetched.json()["vscode_url"] is not None


def test_pause_when_ags_already_paused_is_idempotent(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    world.sandboxes[0].already_paused = True
    response = client.post(f"{SANDBOX}/pause", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paused"
    assert world.sandboxes[0].pause_calls == 1


def test_stopping_sandbox_returns_conflicts(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200
    _update_record(client, user.user_id, status="stopping")

    assert client.post(SANDBOX, headers=headers).status_code == 409
    assert client.post(f"{SANDBOX}/pause", headers=headers).status_code == 409
    assert client.post(f"{SANDBOX}/heartbeat", headers=headers).status_code == 409
    assert client.delete(SANDBOX, headers=headers).status_code == 202

    fetched = client.get(SANDBOX, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "stopping"
    assert fetched.json()["vscode_url"] is None
    assert world.sandboxes[0].killed is False


def test_sandbox_pause_heartbeat_and_resume(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    heartbeat = client.post(f"{SANDBOX}/heartbeat", headers=headers)
    assert heartbeat.status_code == 200, heartbeat.text
    assert heartbeat.json()["status"] == "running"

    paused = client.post(f"{SANDBOX}/pause", headers=headers)
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "paused"
    assert paused.json()["vscode_url"] is None
    assert paused.json()["ttyd_url"] is None
    assert world.sandboxes[0].pause_calls == 1

    connect_calls = world.connect_calls
    fetched = client.get(SANDBOX, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "paused"
    assert world.connect_calls == connect_calls

    paused_heartbeat = client.post(f"{SANDBOX}/heartbeat", headers=headers)
    assert paused_heartbeat.status_code == 200
    assert paused_heartbeat.json()["status"] == "paused"
    assert world.connect_calls == connect_calls

    idempotent_pause = client.post(f"{SANDBOX}/pause", headers=headers)
    assert idempotent_pause.status_code == 200
    assert idempotent_pause.json()["status"] == "paused"
    assert world.sandboxes[0].pause_calls == 1

    resumed = client.post(SANDBOX, headers=headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["sandbox_id"] == "sbx-1"
    assert resumed.json()["status"] == "running"
    assert resumed.json()["paused_at"] is None
    assert resumed.json()["vscode_url"] is not None

    record = _get_record(client, user.user_id)
    assert record is not None
    assert record.status == "running"
    assert record.paused_at is None


def test_delete_failure_keeps_stopping_and_reaper_retries(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    world.kill_fail = True
    failed = client.delete(SANDBOX, headers=headers)
    assert failed.status_code == 503
    record = _get_record(client, user.user_id)
    assert record is not None
    assert record.status == "stopping"

    stopping = client.get(SANDBOX, headers=headers)
    assert stopping.status_code == 200
    assert stopping.json()["status"] == "stopping"
    assert stopping.json()["vscode_url"] is None

    assert client.delete(SANDBOX, headers=headers).status_code == 202

    world.kill_fail = False
    with _session_factory(client)() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=_settings(client),
            now=datetime.now(UTC),
        )
        session.commit()
    assert stats.destroyed == 1
    assert _get_record(client, user.user_id) is None
    assert world.sandboxes[0].killed is True


def test_reaper_pauses_idle_sandbox(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    now = datetime.now(UTC)
    settings = _settings(client)
    _update_record(
        client,
        user.user_id,
        last_active_at=now - timedelta(seconds=settings.ags.sandbox_idle_seconds + 60),
    )

    with _session_factory(client)() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=settings,
            now=now,
        )
        session.commit()

    assert stats.paused == 1
    assert stats.failed == 0
    assert world.sandboxes[0].paused is True
    record = _get_record(client, user.user_id)
    assert record is not None
    assert record.status == "paused"
    assert record.paused_at is not None


def test_reaper_pause_failure_keeps_running(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    now = datetime.now(UTC)
    settings = _settings(client)
    _update_record(
        client,
        user.user_id,
        last_active_at=now - timedelta(seconds=settings.ags.sandbox_idle_seconds + 60),
    )
    world.sandboxes[0].fail_pause = True

    with _session_factory(client)() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=settings,
            now=now,
        )
        session.commit()

    assert stats.paused == 0
    assert stats.failed == 1
    record = _get_record(client, user.user_id)
    assert record is not None
    assert record.status == "running"


def test_reaper_clears_gone_sandbox(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    now = datetime.now(UTC)
    settings = _settings(client)
    _update_record(
        client,
        user.user_id,
        last_active_at=now - timedelta(seconds=settings.ags.sandbox_idle_seconds + 60),
    )
    world.sandboxes.clear()

    with _session_factory(client)() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=settings,
            now=now,
        )
        session.commit()

    assert stats.cleared == 1
    assert stats.failed == 0
    assert _get_record(client, user.user_id) is None


def test_reaper_destroys_expired_paused_sandbox(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    now = datetime.now(UTC)
    settings = _settings(client)
    _update_record(
        client,
        user.user_id,
        status="paused",
        paused_at=now
        - timedelta(seconds=settings.ags.sandbox_paused_retention_seconds + 60),
    )

    with _session_factory(client)() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=settings,
            now=now,
        )
        session.commit()

    assert stats.destroyed == 1
    assert _get_record(client, user.user_id) is None
    assert world.sandboxes[0].killed is True


def test_reaper_destroys_sandbox_over_max_lifetime(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    now = datetime.now(UTC)
    settings = _settings(client)
    _update_record(client, user.user_id, hard_destroy_at=now - timedelta(seconds=1))

    with _session_factory(client)() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=settings,
            now=now,
        )
        session.commit()

    assert stats.destroyed == 1
    assert _get_record(client, user.user_id) is None
    assert world.sandboxes[0].killed is True


def test_reaper_destroys_paused_sandbox_over_max_lifetime(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    now = datetime.now(UTC)
    settings = _settings(client)
    _update_record(
        client,
        user.user_id,
        status="paused",
        paused_at=now - timedelta(minutes=1),
        hard_destroy_at=now - timedelta(seconds=1),
    )

    with _session_factory(client)() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=settings,
            now=now,
        )
        session.commit()

    assert stats.destroyed == 1
    assert _get_record(client, user.user_id) is None
    assert world.sandboxes[0].killed is True


def test_post_after_max_lifetime_recreates_sandbox(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    headers = _login(client)
    assert client.post(SANDBOX, headers=headers).status_code == 200

    _update_record(
        client,
        user.user_id,
        hard_destroy_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    recreated = client.post(SANDBOX, headers=headers)
    assert recreated.status_code == 200, recreated.text
    assert recreated.json()["sandbox_id"] == "sbx-2"
    assert recreated.json()["status"] == "running"
    assert world.sandboxes[0].killed is True

    record = _get_record(client, user.user_id)
    assert record is not None
    assert record.sandbox_id == "sbx-2"
    assert record.hard_destroy_at > datetime.now(UTC)


def test_sandbox_is_isolated_by_user(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login(client, "alice", "password123")
    bob = _login(client, "bob", "password456")

    alice_sandbox = client.post(SANDBOX, headers=alice)
    assert alice_sandbox.status_code == 200
    assert alice_sandbox.json()["sandbox_id"] == "sbx-1"

    assert client.get(SANDBOX, headers=bob).status_code == 404
    bob_sandbox = client.post(SANDBOX, headers=bob)
    assert bob_sandbox.status_code == 200
    assert bob_sandbox.json()["sandbox_id"] == "sbx-2"

    assert client.get(SANDBOX, headers=alice).json()["sandbox_id"] == "sbx-1"
    assert client.get(SANDBOX, headers=bob).json()["sandbox_id"] == "sbx-2"


def test_internal_sandbox_requires_valid_token(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    payload = {"user_id": str(user.user_id)}

    assert client.post(INTERNAL_SANDBOX, json=payload).status_code == 401
    assert (
        client.post(
            INTERNAL_SANDBOX,
            json=payload,
            headers={"X-Internal-Token": "wrong-token"},
        ).status_code
        == 403
    )
    assert world.sandboxes == []


def test_internal_sandbox_creates_and_reuses(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    payload = {"user_id": str(user.user_id)}
    headers = _internal_headers(client)

    created = client.post(INTERNAL_SANDBOX, json=payload, headers=headers)
    assert created.status_code == 200, created.text
    assert created.json() == {"sandbox_id": "sbx-1", "status": "running"}

    reused = client.post(INTERNAL_SANDBOX, json=payload, headers=headers)
    assert reused.status_code == 200, reused.text
    assert reused.json()["sandbox_id"] == "sbx-1"
    assert len(world.sandboxes) == 1


def test_internal_sandbox_rejects_unknown_and_disabled_user(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    disabled = create_user(status=False)
    headers = _internal_headers(client)

    unknown = client.post(
        INTERNAL_SANDBOX,
        json={"user_id": str(uuid4())},
        headers=headers,
    )
    assert unknown.status_code == 404

    blocked = client.post(
        INTERNAL_SANDBOX,
        json={"user_id": str(disabled.user_id)},
        headers=headers,
    )
    assert blocked.status_code == 403
    assert world.sandboxes == []


def test_internal_sandbox_create_failure_returns_503(
    client: TestClient,
    create_user: Callable[..., Users],
    world: FakeWorld,
) -> None:
    user = create_user()
    world.create_fail = True

    response = client.post(
        INTERNAL_SANDBOX,
        json={"user_id": str(user.user_id)},
        headers=_internal_headers(client),
    )
    assert response.status_code == 503
