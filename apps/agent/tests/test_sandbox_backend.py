from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from agent.infra import ags_backend, sandbox_api
from agent.infra.ags_backend import AgsBackend
from agent.infra.sandbox_api import SandboxApiError, ensure_sandbox_id


def test_ensure_sandbox_id_posts_internal_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: object) -> object:
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={"sandbox_id": "sbx-1", "status": "running"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        sandbox_api,
        "get_settings",
        lambda: SimpleNamespace(
            agent_api_base_url="http://api:8000/",
            agent_internal_token="secret",
            agent_api_timeout_seconds=3,
        ),
    )
    monkeypatch.setattr(sandbox_api.httpx, "post", fake_post)

    assert ensure_sandbox_id("user-1") == "sbx-1"
    assert captured["url"] == "http://api:8000/internal/sandbox/ensure"
    assert captured["headers"] == {"X-Internal-Token": "secret"}
    assert captured["json"] == {"user_id": "user-1"}
    assert captured["timeout"] == 3


def test_ensure_sandbox_id_surfaces_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(url: str, **_kwargs: object) -> object:
        return httpx.Response(
            403,
            json={"detail": "内部凭证无效"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        sandbox_api,
        "get_settings",
        lambda: SimpleNamespace(
            agent_api_base_url="http://api:8000",
            agent_internal_token="wrong",
            agent_api_timeout_seconds=3,
        ),
    )
    monkeypatch.setattr(sandbox_api.httpx, "post", fake_post)

    with pytest.raises(SandboxApiError, match="403"):
        ensure_sandbox_id("user-1")


def test_backend_id_uses_api_ensure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ags_backend,
        "get_config",
        lambda: {"configurable": {"langgraph_auth_user_id": "alice"}},
    )
    monkeypatch.setattr(
        ags_backend,
        "ensure_sandbox_id",
        lambda user_id: f"sbx-{user_id}",
    )

    assert AgsBackend().id == "sbx-alice"


def test_backend_id_has_no_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ags_backend, "get_config", lambda: {"configurable": {}})

    with pytest.raises(KeyError):
        _ = AgsBackend().id


def test_backend_caches_and_drops_sandbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connected: list[str] = []

    def fake_connect(sandbox_id: str) -> object:
        connected.append(sandbox_id)
        return object()

    monkeypatch.setattr(
        AgsBackend,
        "id",
        property(lambda _self: "sbx-1"),
    )
    monkeypatch.setattr(ags_backend, "_connect_sandbox", fake_connect)
    backend = AgsBackend()

    first = backend._get_sandbox()
    second = backend._get_sandbox()

    assert first is second
    assert connected == ["sbx-1"]

    backend._drop_sandbox()
    third = backend._get_sandbox()

    assert third is not first
    assert connected == ["sbx-1", "sbx-1"]
