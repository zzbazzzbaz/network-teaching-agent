from types import SimpleNamespace
from typing import Any, cast

import pytest

from agent.infra import ags_backend, sandbox_api
from agent.infra.ags_backend import AgsBackend
from agent.infra.sandbox_api import (
    ResolvedSandbox,
    SandboxApiClient,
    SandboxApiError,
    SandboxManager,
)


def test_sandbox_api_client_posts_internal_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: object) -> object:
        captured["url"] = url
        captured.update(kwargs)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"sandbox_id": "sbx-1", "status": "running"},
        )

    monkeypatch.setattr(sandbox_api.httpx, "post", fake_post)
    client = SandboxApiClient(
        base_url="http://api:8000/",
        internal_token="secret",
        timeout_seconds=3,
    )

    resolved = client.ensure_user_sandbox("user-1")

    assert resolved == ResolvedSandbox(sandbox_id="sbx-1", status="running")
    assert captured["url"] == "http://api:8000/internal/sandbox/ensure"
    assert captured["headers"] == {"X-Internal-Token": "secret"}
    assert captured["json"] == {"user_id": "user-1"}
    assert captured["timeout"] == 3


def test_sandbox_api_client_rejects_missing_token() -> None:
    client = SandboxApiClient(base_url="http://api:8000", internal_token="")

    with pytest.raises(SandboxApiError, match="AGENT_INTERNAL_TOKEN"):
        client.ensure_user_sandbox("user-1")


def test_sandbox_api_client_surfaces_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(_url: str, **_kwargs: object) -> object:
        return SimpleNamespace(
            status_code=403,
            json=lambda: {"detail": "内部凭证无效"},
        )

    monkeypatch.setattr(sandbox_api.httpx, "post", fake_post)
    client = SandboxApiClient(base_url="http://api:8000", internal_token="wrong")

    with pytest.raises(SandboxApiError, match="403"):
        client.ensure_user_sandbox("user-1")


def test_backend_id_reads_auth_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ags_backend,
        "get_config",
        lambda: {"configurable": {"langgraph_auth_user_id": "alice"}},
    )

    assert AgsBackend().id == "alice"


def test_backend_id_has_no_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ags_backend, "get_config", lambda: {"configurable": {}})

    with pytest.raises(KeyError):
        _ = AgsBackend().id


def test_manager_resolves_and_caches_by_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeApiClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def ensure_user_sandbox(self, user_id: str) -> ResolvedSandbox:
            self.calls.append(user_id)
            return ResolvedSandbox(sandbox_id=f"sbx-{user_id}", status="running")

    api_client = FakeApiClient()
    manager = SandboxManager(api_client=cast(SandboxApiClient, api_client))
    monkeypatch.setattr(sandbox_api, "_current_run_id", lambda: None)

    assert manager._ensure_sandbox_id("alice") == "sbx-alice"
    assert manager._ensure_sandbox_id("alice") == "sbx-alice"
    assert manager._ensure_sandbox_id("bob") == "sbx-bob"
    assert api_client.calls == ["alice", "bob"]


def test_manager_re_resolves_for_new_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeApiClient:
        def __init__(self) -> None:
            self.calls = 0

        def ensure_user_sandbox(self, _user_id: str) -> ResolvedSandbox:
            self.calls += 1
            return ResolvedSandbox(sandbox_id=f"sbx-{self.calls}", status="running")

    run_id = "run-1"
    api_client = FakeApiClient()
    manager = SandboxManager(api_client=cast(SandboxApiClient, api_client))
    monkeypatch.setattr(sandbox_api, "_current_run_id", lambda: run_id)

    assert manager._ensure_sandbox_id("alice") == "sbx-1"
    run_id = "run-2"
    assert manager._ensure_sandbox_id("alice") == "sbx-2"
    assert api_client.calls == 2


def test_manager_connects_and_caches_sandbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connected: list[str] = []

    class FakeApiClient:
        def ensure_user_sandbox(self, _user_id: str) -> ResolvedSandbox:
            return ResolvedSandbox(sandbox_id="sbx-1", status="running")

    def fake_connect(sandbox_id: str) -> object:
        connected.append(sandbox_id)
        return object()

    manager = SandboxManager(api_client=cast(SandboxApiClient, FakeApiClient()))
    monkeypatch.setattr(sandbox_api, "_current_run_id", lambda: None)
    monkeypatch.setattr(sandbox_api, "_connect_sandbox", fake_connect)

    first = manager.get_sandbox("alice")
    second = manager.get_sandbox("alice")

    assert first is second
    assert connected == ["sbx-1"]


def test_manager_wraps_api_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingApiClient:
        def ensure_user_sandbox(self, _user_id: str) -> ResolvedSandbox:
            raise SandboxApiError("沙箱服务暂不可用")

    manager = SandboxManager(api_client=cast(SandboxApiClient, FailingApiClient()))
    monkeypatch.setattr(sandbox_api, "_current_run_id", lambda: None)

    with pytest.raises(RuntimeError, match="沙箱服务暂不可用"):
        manager._ensure_sandbox_id("alice")
