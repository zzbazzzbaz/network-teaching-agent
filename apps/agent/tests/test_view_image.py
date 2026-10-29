from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any, Protocol, cast

import pytest

import agent.tools.files as files_module
from agent.infra.files_api import FileApiError, FileMetadata, FileNotFound
from agent.tools.files import make_view_image


class _AsyncTool(Protocol):
    async def coroutine(
        self,
        *,
        file_id: str,
        runtime: object,
    ) -> tuple[str, dict[str, Any]]: ...


def _runtime() -> SimpleNamespace:
    return SimpleNamespace(
        config={
            "configurable": {
                "langgraph_auth_user_id": "user-1",
                "thread_id": "thread-1",
            }
        },
        tool_call_id="call-1",
    )


def _invoke(file_id: str) -> tuple[str, dict[str, Any]]:
    tool = cast(_AsyncTool, make_view_image())
    return asyncio.run(tool.coroutine(file_id=file_id, runtime=_runtime()))


def test_view_image_returns_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    file_id = uuid.uuid4()

    async def fake_metadata(user_id: str, raw_file_id: str) -> FileMetadata:
        assert user_id == "user-1"
        assert raw_file_id == str(file_id)
        return FileMetadata(
            file_id=file_id,
            name="题目.png",
            mime="image/png",
            size_bytes=123,
        )

    monkeypatch.setattr(files_module, "get_file_metadata", fake_metadata)
    content, artifact = _invoke(str(file_id))

    assert "已加载" in content
    assert artifact == {"images": [{"file_id": str(file_id), "name": "题目.png"}]}


def test_view_image_missing_file_is_natural_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_metadata(user_id: str, file_id: str) -> FileMetadata:
        raise FileNotFound("gone")

    monkeypatch.setattr(files_module, "get_file_metadata", fake_metadata)
    content, artifact = _invoke(str(uuid.uuid4()))

    assert "不存在" in content
    assert artifact == {"images": []}


def test_view_image_service_error_is_natural_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_metadata(user_id: str, file_id: str) -> FileMetadata:
        raise FileApiError("down")

    monkeypatch.setattr(files_module, "get_file_metadata", fake_metadata)
    content, artifact = _invoke(str(uuid.uuid4()))

    assert "暂不可用" in content
    assert artifact == {"images": []}


def test_view_image_rejects_invalid_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_metadata(user_id: str, file_id: str) -> FileMetadata:
        raise AssertionError("invalid uuid should not call the API")

    monkeypatch.setattr(files_module, "get_file_metadata", fake_metadata)
    content, artifact = _invoke("not-a-uuid")

    assert "格式不正确" in content
    assert artifact == {"images": []}
