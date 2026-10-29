import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Protocol, cast

import pytest

import agent.tools.question_bank as question_bank_module
from agent.infra.question_bank_api import (
    KnowledgePointRef,
    QuestionBankError,
    SaveQuestionResponse,
    SearchItem,
    SearchResponse,
)
from agent.runtime.context import ToolContext
from agent.tools.question_bank import make_question_bank_tools
from agent.tools.schemas.question import Question
from agent.tools.schemas.question_bank import SearchQuestionsInput


class _ToolWithFunc(Protocol):
    func: Callable[..., str]


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


def _tools() -> dict[str, _ToolWithFunc]:
    return {
        tool.name: cast(_ToolWithFunc, tool)
        for tool in make_question_bank_tools()
    }


def test_search_questions_formats_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_search(context: ToolContext, query: SearchQuestionsInput) -> SearchResponse:
        captured["context"] = context
        captured["query"] = query
        return SearchResponse(
            items=[
                SearchItem(
                    question_id=uuid.uuid4(),
                    origin="mine",
                    question_type="single_choice",
                    stem_preview="TCP 慢开始阶段 cwnd 如何变化？",
                    primary_knowledge_point=KnowledgePointRef(
                        id="5.8.2",
                        title="TCP的拥塞控制方法",
                    ),
                    secondary_knowledge_points=[],
                    last_attempt_at="2026-10-28T10:00:00Z",
                )
            ],
            total=1,
            limit=10,
            offset=0,
        )

    monkeypatch.setattr(question_bank_module, "search_questions_api", fake_search)
    result = _tools()["search_questions"].func(
        scope="mine",
        knowledge_point_id="5.8.2",
        runtime=_runtime(),
    )

    assert "共 1 条" in result
    assert "[mine] single_choice · 5.8.2 TCP的拥塞控制方法" in result
    assert "上次作答：2026-10-28T10:00:00Z" in result
    context = captured["context"]
    assert isinstance(context, ToolContext)
    assert context.user_id == "user-1"
    query_value = captured["query"]
    assert isinstance(query_value, SearchQuestionsInput)
    assert query_value.scope == "mine"


def test_search_questions_returns_error_without_fabricating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_search(context: ToolContext, query: SearchQuestionsInput) -> SearchResponse:
        raise QuestionBankError("题库服务不可用")

    monkeypatch.setattr(question_bank_module, "search_questions_api", fake_search)
    result = _tools()["search_questions"].func(runtime=_runtime())

    assert "题库检索失败" in result
    assert "TCP" not in result


def test_search_questions_requires_auth() -> None:
    runtime = SimpleNamespace(config={"configurable": {}}, tool_call_id="call-1")

    with pytest.raises(KeyError):
        _tools()["search_questions"].func(runtime=runtime)


def test_save_question(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_save(context: ToolContext, question: Question) -> SaveQuestionResponse:
        captured["context"] = context
        captured["question"] = question
        return SaveQuestionResponse(question_id=uuid.uuid4())

    monkeypatch.setattr(question_bank_module, "save_question_api", fake_save)
    question = Question(
        mode="short_answer",
        stem="为什么？",
        reference_answer="因为要匹配原始探测包",
        primary_knowledge_point_id="4.4.1",
    )

    result = _tools()["save_question"].func(question=question, runtime=_runtime())

    assert "已保存到学生的私人题库" in result
    context = captured["context"]
    assert isinstance(context, ToolContext)
    assert context.user_id == "user-1"
    assert captured["question"] is question


def test_save_question_sends_plain_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_save(context: ToolContext, question: Question) -> SaveQuestionResponse:
        captured["question"] = question
        return SaveQuestionResponse(question_id=uuid.uuid4())

    monkeypatch.setattr(question_bank_module, "save_question_api", fake_save)
    question = Question(
        mode="single_choice",
        stem="选一个",
        options=["直接转发", "回 ICMP Time Exceeded"],
        correct_option="B",
        primary_knowledge_point_id="4.2.5",
    )

    _tools()["save_question"].func(question=question, runtime=_runtime())

    saved = captured["question"]
    assert isinstance(saved, Question)
    assert saved.options == ["直接转发", "回 ICMP Time Exceeded"]


def test_save_question_returns_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_save(context: ToolContext, question: Question) -> SaveQuestionResponse:
        raise QuestionBankError("题库服务返回 422：options: 选项内容不能为空")

    monkeypatch.setattr(question_bank_module, "save_question_api", fake_save)

    result = _tools()["save_question"].func(
        question=Question(
            mode="short_answer",
            stem="为什么？",
            primary_knowledge_point_id="4.4.1",
        ),
        runtime=_runtime(),
    )

    assert "题目保存失败" in result
    assert "选项内容不能为空" in result
