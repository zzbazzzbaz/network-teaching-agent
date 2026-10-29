from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from types import SimpleNamespace
from typing import cast

import pytest
from deepagents import create_deep_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

import agent.runtime.session_title as session_title_module
from agent.infra.session_api import (
    SessionTitleError,
    SessionTitleNotFound,
    SessionTitleResult,
)
from agent.runtime.session_title import (
    SessionTitleMiddleware,
    SessionTitleState,
    _sanitize_title,
)


class _FakeAgentModel(FakeMessagesListChatModel):
    def bind_tools(
        self,
        tools: Sequence[object],
        *,
        tool_choice: str | None = None,
        **kwargs: object,
    ) -> _FakeAgentModel:
        return self


class _FakeLLM:
    def __init__(
        self,
        text: str = "TCP 三次握手",
        *,
        error: Exception | None = None,
    ) -> None:
        self.text = text
        self.error = error
        self.calls: list[list[BaseMessage]] = []
        self.bind_kwargs: dict[str, object] | None = None

    def bind(self, **kwargs: object) -> _FakeLLM:
        self.bind_kwargs = kwargs
        return self

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
    ) -> AIMessage:
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return AIMessage(content=self.text)


def _state(
    *,
    human: str | None = "TCP 为什么需要三次握手？",
    assistant: str | None = "因为双方需要确认彼此的收发能力。",
    generated: bool | None = None,
) -> SessionTitleState:
    messages: list[BaseMessage] = []
    if human is not None:
        messages.append(HumanMessage(content=human))
    if assistant is not None:
        messages.append(AIMessage(content=assistant))
    state: dict[str, object] = {"messages": messages}
    if generated is not None:
        state["session_title_generated"] = generated
    return cast(SessionTitleState, state)


def _config(
    monkeypatch: pytest.MonkeyPatch,
    *,
    user_id: str = "user-1",
    thread_id: str = "thread-1",
) -> None:
    monkeypatch.setattr(
        session_title_module,
        "get_config",
        lambda: {
            "configurable": {
                "langgraph_auth_user_id": user_id,
                "thread_id": thread_id,
            }
        },
    )


def _run(middleware: SessionTitleMiddleware, state: SessionTitleState) -> object:
    return asyncio.run(middleware.aafter_agent(state, cast(Runtime[None], SimpleNamespace())))


def test_title_generated_on_first_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _FakeLLM("“TCP 三次握手。”")
    calls: list[tuple[str, str, str]] = []

    async def fake_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        calls.append((user_id, thread_id, title))
        return SessionTitleResult(updated=True, title=title, reason="updated")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(session_title_module, "set_session_title", fake_set_session_title)

    result = _run(SessionTitleMiddleware(), _state())

    assert result == {"session_title_generated": True}
    assert calls == [("user-1", "thread-1", "TCP 三次握手")]
    assert llm.bind_kwargs == {
        "reasoning_effort": "none",
        "max_tokens": 64,
        "temperature": 0,
    }
    assert len(llm.calls) == 1
    assert "TCP 为什么需要三次握手？" in llm.calls[0][1].text


def test_title_skipped_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_llm() -> None:
        raise AssertionError("不应该调用模型")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", fail_llm)

    result = _run(SessionTitleMiddleware(), _state(generated=True))

    assert result is None


def test_title_sets_flag_when_not_default(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _FakeLLM("TCP 三次握手")
    calls: list[str] = []

    async def fake_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        calls.append(title)
        return SessionTitleResult(updated=False, title="手动标题", reason="not_default")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(session_title_module, "set_session_title", fake_set_session_title)

    result = _run(SessionTitleMiddleware(), _state())

    assert result == {"session_title_generated": True}
    assert calls == ["TCP 三次握手"]


def test_title_retries_on_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _FakeLLM("TCP 三次握手")
    attempts = 0

    async def flaky_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise SessionTitleError("down")
        return SessionTitleResult(updated=True, title=title, reason="updated")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(session_title_module, "set_session_title", flaky_set_session_title)

    middleware = SessionTitleMiddleware()
    first = _run(middleware, _state())
    second = _run(middleware, _state())

    assert first is None
    assert second == {"session_title_generated": True}
    assert attempts == 2


def test_title_sets_flag_when_session_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def missing(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        raise SessionTitleNotFound("missing")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: _FakeLLM())
    monkeypatch.setattr(session_title_module, "set_session_title", missing)

    result = _run(SessionTitleMiddleware(), _state())

    assert result == {"session_title_generated": True}


def test_title_skipped_without_human_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_llm() -> None:
        raise AssertionError("不应该调用模型")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", fail_llm)

    result = _run(
        SessionTitleMiddleware(),
        _state(human=None, assistant="老师先问你一个问题"),
    )

    assert result is None


def test_title_skipped_without_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_llm() -> None:
        raise AssertionError("不应该调用模型")

    monkeypatch.setattr(session_title_module, "get_config", lambda: {})
    monkeypatch.setattr(session_title_module, "get_llm", fail_llm)

    result = _run(SessionTitleMiddleware(), _state())

    assert result is None


def test_title_skipped_when_model_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = _FakeLLM("")

    async def fail_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        raise AssertionError("不应该写入标题")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(
        session_title_module,
        "set_session_title",
        fail_set_session_title,
    )

    result = _run(SessionTitleMiddleware(), _state())

    assert result is None


def test_title_skipped_when_model_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = _FakeLLM(error=RuntimeError("model down"))

    async def fail_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        raise AssertionError("不应该写入标题")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(
        session_title_module,
        "set_session_title",
        fail_set_session_title,
    )

    result = _run(SessionTitleMiddleware(), _state())

    assert result is None


def test_prompt_uses_first_human_and_first_ai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = _FakeLLM("TCP 三次握手")

    async def fake_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        return SessionTitleResult(updated=True, title=title, reason="updated")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(session_title_module, "set_session_title", fake_set_session_title)

    state = cast(
        SessionTitleState,
        {
            "messages": [
                HumanMessage(content="第一条学生消息"),
                AIMessage(content="第一条助手回复"),
                HumanMessage(content="第二条学生消息"),
                AIMessage(content="第二条助手回复"),
            ]
        },
    )
    _run(SessionTitleMiddleware(), state)

    payload = llm.calls[0][1].text
    assert "第一条学生消息" in payload
    assert "第一条助手回复" in payload
    assert "第二条学生消息" not in payload
    assert "第二条助手回复" not in payload


def test_compiled_graph_invokes_session_title(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _FakeLLM("TCP 三次握手")
    calls: list[tuple[str, str, str]] = []

    async def fake_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        calls.append((user_id, thread_id, title))
        return SessionTitleResult(updated=True, title=title, reason="updated")

    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(session_title_module, "set_session_title", fake_set_session_title)

    graph = create_deep_agent(
        model=_FakeAgentModel(responses=[AIMessage(content="三次握手是为了确认双方的收发能力。")]),
        system_prompt="你是计算机网络老师。",
        middleware=[SessionTitleMiddleware()],
    )
    result = asyncio.run(
        graph.ainvoke(
            {"messages": [HumanMessage(content="TCP 为什么需要三次握手？")]},
            config={
                "configurable": {
                    "thread_id": "thread-1",
                    "langgraph_auth_user_id": "user-1",
                }
            },
        )
    )

    assert calls == [("user-1", "thread-1", "TCP 三次握手")]
    assert result["session_title_generated"] is True


def test_sanitize_title_removes_labels_and_punctuation() -> None:
    assert _sanitize_title("标题：TCP 三次握手。") == "TCP 三次握手"
    assert _sanitize_title("“TCP 三次握手”") == "TCP 三次握手"
    assert _sanitize_title("  TCP   三次握手  ") == "TCP 三次握手"


def test_sanitize_title_rejects_default_and_empty() -> None:
    assert _sanitize_title("新会话") is None
    assert _sanitize_title("  ") is None
    assert _sanitize_title("好") is None


def test_sanitize_title_truncates_long_output() -> None:
    assert _sanitize_title("x" * 40) == "x" * 24


def test_empty_title_is_logged_and_not_written(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    llm = _FakeLLM("")

    async def unexpected_set_session_title(
        *,
        user_id: str,
        thread_id: str,
        title: str,
    ) -> SessionTitleResult:
        raise AssertionError("标题为空时不应该写入")

    _config(monkeypatch)
    monkeypatch.setattr(session_title_module, "get_llm", lambda: llm)
    monkeypatch.setattr(
        session_title_module,
        "set_session_title",
        unexpected_set_session_title,
    )

    with caplog.at_level(logging.WARNING, logger=session_title_module.__name__):
        result = _run(SessionTitleMiddleware(), _state())

    assert result is None
    assert "会话标题为空或无效" in caplog.text
