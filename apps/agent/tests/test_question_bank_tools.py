from collections.abc import Callable
from types import SimpleNamespace
from typing import Protocol, cast

import pytest

import agent.tools.question_bank as question_bank_module
from agent.infra.question_bank_api import QuestionBankApiError
from agent.tools.question_bank import make_question_bank_tools
from agent.tools.schemas.question_bank import SaveQuestionInput, SearchQuestionsInput


class _ToolWithFunc(Protocol):
    func: Callable[..., str]


def _runtime() -> SimpleNamespace:
    return SimpleNamespace(
        config={"configurable": {"langgraph_auth_user_id": "user-1"}},
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

    def fake_search(user_id: str, query: SearchQuestionsInput) -> dict[str, object]:
        captured["user_id"] = user_id
        captured["query"] = query
        return {
            "total": 1,
            "limit": 10,
            "offset": 0,
            "items": [
                {
                    "question_id": "q-1",
                    "origin": "mine",
                    "question_type": "single_choice",
                    "stem_preview": "TCP 慢开始阶段 cwnd 如何变化？",
                    "primary_knowledge_point": {
                        "id": "5.8.2",
                        "title": "TCP的拥塞控制方法",
                    },
                    "secondary_knowledge_points": [],
                    "last_attempt_at": "2026-10-28T10:00:00Z",
                }
            ],
        }

    monkeypatch.setattr(question_bank_module, "search_questions_api", fake_search)
    tool_obj = _tools()["search_questions"]
    result = tool_obj.func(
        scope="mine",
        knowledge_point_id="5.8.2",
        runtime=_runtime(),
    )

    assert "共 1 条" in result
    assert "[mine] single_choice · 5.8.2 TCP的拥塞控制方法" in result
    assert "上次作答：2026-10-28T10:00:00Z" in result
    assert captured["user_id"] == "user-1"
    query_value = captured["query"]
    assert isinstance(query_value, SearchQuestionsInput)
    assert query_value.scope == "mine"


def test_search_questions_returns_error_without_fabricating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_search(user_id: str, query: SearchQuestionsInput) -> dict[str, object]:
        raise QuestionBankApiError("题库服务不可用")

    monkeypatch.setattr(question_bank_module, "search_questions_api", fake_search)
    result = _tools()["search_questions"].func(runtime=_runtime())

    assert "题库检索失败" in result
    assert "TCP" not in result


def test_search_questions_requires_auth() -> None:
    runtime = SimpleNamespace(config={"configurable": {}}, tool_call_id="call-1")
    result = _tools()["search_questions"].func(runtime=runtime)

    assert "未认证" in result


def test_save_question(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_save(user_id: str, question: SaveQuestionInput) -> dict[str, object]:
        captured["user_id"] = user_id
        captured["question"] = question
        return {"question_id": "q-1"}

    monkeypatch.setattr(question_bank_module, "save_question_api", fake_save)
    result = _tools()["save_question"].func(
        question_type="short_answer",
        stem="为什么？",
        reference_answer="因为要匹配原始探测包",
        primary_knowledge_point_id="4.4.1",
        runtime=_runtime(),
    )

    assert "已保存到我的题库" in result
    assert captured["user_id"] == "user-1"
    question_value = captured["question"]
    assert isinstance(question_value, SaveQuestionInput)
    assert question_value.question_type == "short_answer"


def test_save_question_rejects_public_single_choice_without_answer() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _tools()["save_question"].func(
            question_type="single_choice",
            stem="选一个",
            options=["A. 一", "B. 二"],
            primary_knowledge_point_id="5.8.2",
            runtime=_runtime(),
        )
