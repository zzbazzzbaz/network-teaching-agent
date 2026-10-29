from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterator, Sequence
from typing import ClassVar

import pytest
from langchain.agents import create_agent
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

import agent.runtime.image_attachments as image_module
from agent.infra.files_api import FileMetadata
from agent.runtime.image_attachments import (
    ImageAttachmentMiddleware,
    clear_image_cache,
)

PNG = b"\x89PNG\r\n\x1a\nfake-image-bytes"


class _RecordingModel(FakeMessagesListChatModel):
    received: ClassVar[list[list[BaseMessage]]] = []

    def bind_tools(self, tools: object, **kwargs: object) -> _RecordingModel:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: object | None = None,
        **kwargs: object,
    ) -> ChatResult:
        self.received.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="ok"))])


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    clear_image_cache()
    yield
    clear_image_cache()


def _ref(file_id: uuid.UUID, name: str = "题目.png") -> dict[str, str]:
    return {"file_id": str(file_id), "name": name}


def _human(text: str, refs: list[dict[str, str]]) -> HumanMessage:
    return HumanMessage(
        content=text,
        additional_kwargs={"attachments": refs},
    )


def _has_image(message: BaseMessage) -> bool:
    return isinstance(message.content, list) and any(
        isinstance(part, dict) and part.get("type") == "image_url"
        for part in message.content
    )


def _text(message: BaseMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    return "\n".join(
        str(part.get("text", ""))
        for part in message.content
        if isinstance(part, dict)
    )


def _run(
    monkeypatch: pytest.MonkeyPatch,
    messages: Sequence[AnyMessage],
    *,
    sizes: dict[uuid.UUID, int] | None = None,
    metadata_error: Exception | None = None,
    raw_error: Exception | None = None,
) -> tuple[list[AnyMessage], list[tuple[str, str]]]:
    calls: list[tuple[str, str]] = []
    size_map = sizes or {}

    async def fake_metadata(user_id: str, file_id: str) -> FileMetadata:
        calls.append(("metadata", file_id))
        if metadata_error is not None:
            raise metadata_error
        parsed = uuid.UUID(file_id)
        return FileMetadata(
            file_id=parsed,
            name=f"image-{file_id[:8]}.png",
            mime="image/png",
            size_bytes=size_map.get(parsed, len(PNG)),
        )

    async def fake_raw(user_id: str, file_id: str) -> tuple[bytes, str]:
        calls.append(("raw", file_id))
        if raw_error is not None:
            raise raw_error
        return PNG, "image/png"

    monkeypatch.setattr(image_module, "get_file_metadata", fake_metadata)
    monkeypatch.setattr(image_module, "get_file_raw", fake_raw)
    monkeypatch.setattr(
        image_module,
        "get_config",
        lambda: {
            "configurable": {
                "langgraph_auth_user_id": "user-1",
                "thread_id": "thread-1",
            }
        },
    )

    seen: list[ModelRequest[None]] = []
    ordered = list(messages)

    async def handler(request: ModelRequest[None]) -> ModelResponse[None]:
        seen.append(request)
        return ModelResponse(result=[AIMessage(content="ok")])

    request = ModelRequest(
        model=FakeMessagesListChatModel(responses=[AIMessage(content="ok")]),
        messages=ordered,
        state=None,
        runtime=None,
    )
    asyncio.run(ImageAttachmentMiddleware().awrap_model_call(request, handler))
    return list(seen[-1].messages), calls


def test_only_last_three_human_turns_are_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[AnyMessage] = []
    humans: list[HumanMessage] = []
    for index in range(5):
        human = _human(f"第 {index} 轮", [_ref(uuid.uuid4(), f"图{index}.png")])
        humans.append(human)
        messages.append(human)
        messages.append(AIMessage(content=f"回答 {index}"))

    rewritten, calls = _run(monkeypatch, messages)
    rewritten_humans = [m for m in rewritten if isinstance(m, HumanMessage)]

    assert len(rewritten_humans) == 5
    assert not _has_image(rewritten_humans[0])
    assert not _has_image(rewritten_humans[1])
    assert all(_has_image(m) for m in rewritten_humans[2:])
    assert "图片已卸载" in _text(rewritten_humans[0])
    assert len([call for call in calls if call[0] == "metadata"]) == 3
    assert isinstance(humans[0].content, str)


def test_single_turn_limits_to_three_images(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refs = [_ref(uuid.uuid4(), f"图{index}.png") for index in range(4)]
    messages = [_human("四张图", refs)]

    rewritten, _ = _run(monkeypatch, messages)
    human = rewritten[0]
    assert isinstance(human, HumanMessage)
    assert _has_image(human)
    assert isinstance(human.content, list)
    assert sum(
        1
        for part in human.content
        if isinstance(part, dict) and part.get("type") == "image_url"
    ) == 3
    assert "还有 1 张图片未加载" in _text(human)


def test_total_image_budget_prefers_recent_turns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[AnyMessage] = []
    for index in range(3):
        messages.append(
            _human(
                f"第 {index} 轮",
                [_ref(uuid.uuid4(), f"图{index}-{item}.png") for item in range(3)],
            )
        )
        messages.append(AIMessage(content=f"回答 {index}"))

    rewritten, _ = _run(monkeypatch, messages)
    humans = [m for m in rewritten if isinstance(m, HumanMessage)]

    assert not _has_image(humans[0])
    assert "还有 3 张图片未加载" in _text(humans[0])
    assert _has_image(humans[1])
    assert _has_image(humans[2])


def test_image_over_total_budget_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = uuid.uuid4()
    messages = [_human("大图", [_ref(file_id)])]

    rewritten, calls = _run(
        monkeypatch,
        messages,
        sizes={file_id: 6 * 1024 * 1024 + 1},
    )
    human = rewritten[0]
    assert isinstance(human, HumanMessage)
    assert not _has_image(human)
    assert "图片过大，未加载" in _text(human)
    assert ("raw", str(file_id)) not in calls


def test_current_turn_tool_artifact_is_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attachment_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    messages: list[AnyMessage] = [
        _human("先看这张", [_ref(attachment_id)]),
        AIMessage(content="我看看", tool_calls=[]),
        ToolMessage(
            content="已加载图片",
            tool_call_id="call-1",
            artifact={"images": [{"file_id": str(tool_id), "name": "旧图.png"}]},
        ),
    ]

    rewritten, _ = _run(monkeypatch, messages)
    human = next(m for m in rewritten if isinstance(m, HumanMessage))
    assert isinstance(human.content, list)
    assert sum(
        1
        for part in human.content
        if isinstance(part, dict) and part.get("type") == "image_url"
    ) == 2


def test_tool_can_load_fourth_image_from_same_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refs = [_ref(uuid.uuid4(), f"图{index}.png") for index in range(4)]
    messages: list[AnyMessage] = [
        _human("四张图", refs),
        ToolMessage(
            content="已加载第四张",
            tool_call_id="call-1",
            artifact={"images": [{"file_id": refs[3]["file_id"], "name": "图3.png"}]},
        ),
    ]

    rewritten, _ = _run(monkeypatch, messages)
    human = next(m for m in rewritten if isinstance(m, HumanMessage))
    assert isinstance(human.content, list)
    assert sum(
        1
        for part in human.content
        if isinstance(part, dict) and part.get("type") == "image_url"
    ) == 4
    assert "还有" not in _text(human)


def test_previous_turn_tool_artifact_is_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_id = uuid.uuid4()
    messages: list[AnyMessage] = [
        _human("第一轮", [_ref(uuid.uuid4())]),
        ToolMessage(
            content="已加载旧图",
            tool_call_id="call-1",
            artifact={"images": [{"file_id": str(tool_id), "name": "旧图.png"}]},
        ),
        AIMessage(content="回答"),
        _human("第二轮", [_ref(uuid.uuid4())]),
    ]

    _, calls = _run(monkeypatch, messages)
    assert ("metadata", str(tool_id)) not in calls


def test_missing_image_does_not_break_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent.infra.files_api import FileNotFound

    messages = [_human("图没了", [_ref(uuid.uuid4())])]
    rewritten, _ = _run(monkeypatch, messages, metadata_error=FileNotFound("gone"))

    human = rewritten[0]
    assert isinstance(human, HumanMessage)
    assert not _has_image(human)
    assert "图片不可用" in _text(human)


def test_image_cache_avoids_repeated_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = uuid.uuid4()
    messages = [_human("同一张图", [_ref(file_id)])]

    _run(monkeypatch, messages)
    _, calls = _run(monkeypatch, messages)

    assert len([call for call in calls if call[0] == "metadata"]) == 0
    assert len([call for call in calls if call[0] == "raw"]) == 0


def test_original_request_is_not_mutated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = uuid.uuid4()
    original = _human("原始消息", [_ref(file_id)])
    messages = [original]

    rewritten, _ = _run(monkeypatch, messages)

    assert original.content == "原始消息"
    assert original.additional_kwargs["attachments"][0]["file_id"] == str(file_id)
    assert rewritten[0] is not original


def test_middleware_works_inside_agent_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_image_cache()
    file_id = uuid.uuid4()
    _RecordingModel.received = []

    async def fake_metadata(user_id: str, raw_file_id: str) -> FileMetadata:
        return FileMetadata(
            file_id=file_id,
            name="题目.png",
            mime="image/png",
            size_bytes=len(PNG),
        )

    async def fake_raw(user_id: str, raw_file_id: str) -> tuple[bytes, str]:
        return PNG, "image/png"

    monkeypatch.setattr(image_module, "get_file_metadata", fake_metadata)
    monkeypatch.setattr(image_module, "get_file_raw", fake_raw)

    agent = create_agent(
        model=_RecordingModel(responses=[]),
        tools=[],
        middleware=[ImageAttachmentMiddleware()],
    )
    asyncio.run(
        agent.ainvoke(
            {"messages": [_human("这道题怎么做", [_ref(file_id)])]},
            config={
                "configurable": {
                    "langgraph_auth_user_id": "user-1",
                    "thread_id": "thread-1",
                }
            },
        )
    )

    assert _RecordingModel.received
    assert any(_has_image(message) for message in _RecordingModel.received[-1])
