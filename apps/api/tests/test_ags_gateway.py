from types import SimpleNamespace
from typing import cast

import pytest

from app.core.config import Settings
from app.gateway import ags


def test_create_sandbox_uses_auto_pause_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_create(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr("app.gateway.ags.Sandbox.create", fake_create)
    settings = cast(
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
