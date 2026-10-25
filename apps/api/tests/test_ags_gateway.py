from types import SimpleNamespace
from typing import cast

import pytest

from app.core.config import Settings
from app.gateway import ags


def _settings() -> Settings:
    return cast(
        Settings,
        SimpleNamespace(
            ags=SimpleNamespace(
                tool_name="test-tool",
                sandbox_timeout_seconds=3600,
            ),
            e2b=SimpleNamespace(
                api_key="test-key",
                domain="example.test",
            ),
        ),
    )


def test_create_sandbox_uses_auto_pause_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_create(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr("app.gateway.ags.Sandbox.create", fake_create)
    settings = _settings()

    sandbox = ags.create_sandbox(settings, user_id="user-1")

    assert sandbox is sentinel
    assert captured["template"] == "test-tool"
    assert captured["timeout"] == 3600
    assert captured["metadata"] == {"user_id": "user-1"}
    assert captured["network"] == {"allow_public_traffic": True}
    assert captured["lifecycle"] == {
        "on_timeout": "pause",
        "auto_resume": False,
    }


def test_connect_sandbox_passes_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_connect(sandbox_id: str, **kwargs: object) -> object:
        captured["sandbox_id"] = sandbox_id
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr("app.gateway.ags.Sandbox.connect", fake_connect)

    sandbox = ags.connect_sandbox(_settings(), "sbx-1", timeout=1800)

    assert sandbox is sentinel
    assert captured["sandbox_id"] == "sbx-1"
    assert captured["timeout"] == 1800
    assert captured["api_key"] == "test-key"
    assert captured["domain"] == "example.test"


def test_pause_sandbox_uses_static_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_pause(sandbox_id: str, **kwargs: object) -> bool:
        captured["sandbox_id"] = sandbox_id
        captured.update(kwargs)
        return False

    monkeypatch.setattr("app.gateway.ags.Sandbox.pause", fake_pause)

    assert ags.pause_sandbox(_settings(), "sbx-1") is False
    assert captured["sandbox_id"] == "sbx-1"
    assert captured["api_key"] == "test-key"
    assert captured["domain"] == "example.test"
