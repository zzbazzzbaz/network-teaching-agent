import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, Protocol, cast

import pytest
from langgraph.prebuilt import ToolRuntime
from pydantic import ValidationError

from agent.infra.question_bank_api import (
    AskStudentRecordResponse,
    QuestionBankError,
    QuestionReference,
)
from agent.runtime.context import ToolContext, tool_context
from agent.tools.ask_student import make_ask_student
from agent.tools.schemas.ask_student import AskStudentInput, AskStudentResume
from agent.tools.schemas.question import AskQuestion, Question


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


def _question(**overrides: object) -> AskQuestion:
    data: dict[str, Any] = {
        "mode": "single_choice",
        "stem": "TTL=1 时第一台路由器会做什么？",
        "options": ["直接转发", "回 ICMP Time Exceeded"],
        "correct_option": "B",
        "primary_knowledge_point_id": "4.2.5",
    }
    data.update(overrides)
    return AskQuestion(**data)


def test_plain_text_options_from_incident_are_accepted() -> None:
    question = AskStudentInput(
        question={
            "mode": "single_choice",
            "stem": (
                "教材 2.1 开头先说明物理层要「屏蔽掉传输媒体和通信手段的差异」，"
                "然后才给出物理层的主要任务。\n\n"
                "下面哪一项属于物理层的**主要任务**？"
            ),
            "options": [
                "规定与传输媒体接口有关的机械、电气、功能和过程特性",
                "决定这次布线使用双绞线、同轴电缆还是光纤",
                "规定某种传输媒体的材料成分、屏蔽方式与最大传输距离",
                "比较各种传输媒体的价格并选出最经济的一种",
            ],
            "correct_option": "A",
            "primary_knowledge_point_id": "2.1",
        }
    ).question

    payload = question.to_payload()
    assert payload["options"] == question.options
    assert payload["answer"] == {"correct_option": "A"}


def test_ask_question_rejects_missing_options_at_question_loc() -> None:
    with pytest.raises(ValidationError) as exc_info:
        AskStudentInput(
            question={
                "mode": "single_choice",
                "stem": "选一个",
                "correct_option": "A",
                "primary_knowledge_point_id": "5.8.2",
            }
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("question",) for error in errors)
    assert "单选题必须提供 2–6 个选项" in str(exc_info.value)


def test_ask_question_rejects_duplicate_options() -> None:
    with pytest.raises(ValidationError, match="选项内容不能重复"):
        _question(options=["同一个", "同一个"])


def test_ask_question_rejects_out_of_range_correct_option() -> None:
    with pytest.raises(ValidationError, match="correct_option 必须是选项字母之一"):
        _question(correct_option="C")


def test_short_answer_rejects_options() -> None:
    with pytest.raises(ValidationError, match="简答题不能提供 options"):
        AskQuestion(
            mode="short_answer",
            stem="解释一下",
            options=["错误"],
            primary_knowledge_point_id="5.8.2",
        )


def test_single_choice_rejects_reference_answer() -> None:
    with pytest.raises(ValidationError, match="单选题不能提供 reference_answer"):
        _question(reference_answer="B 是对的")


def test_plain_single_choice_payload() -> None:
    payload = _question().to_payload()

    assert payload == {
        "type": "ask_student",
        "mode": "single_choice",
        "question": "TTL=1 时第一台路由器会做什么？",
        "options": ["直接转发", "回 ICMP Time Exceeded"],
        "answer": {"correct_option": "B"},
    }


def test_short_answer_payload_contains_reference_answer() -> None:
    question = AskQuestion(
        mode="short_answer",
        stem="为什么？",
        placeholder="用一句话说明",
        reference_answer="为了匹配原始探测包",
        primary_knowledge_point_id="4.4.1",
    )

    assert question.to_payload() == {
        "type": "ask_student",
        "mode": "short_answer",
        "question": "为什么？",
        "placeholder": "用一句话说明",
        "answer": {"reference_answer": "为了匹配原始探测包"},
    }


def test_tool_interrupt_payload_and_recorder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.ask_student as ask_student_module

    captured: dict[str, object] = {}

    def fake_interrupt(
        payload: dict[str, object],
        *,
        response_schema: type[AskStudentResume],
    ) -> AskStudentResume:
        captured["payload"] = payload
        captured["response_schema"] = response_schema
        return AskStudentResume(answer="b")

    def fake_record(
        *,
        context: ToolContext,
        question: Question,
        answer: str,
    ) -> AskStudentRecordResponse:
        captured["context"] = context
        captured["question"] = question
        captured["answer"] = answer
        return AskStudentRecordResponse(
            question_id=uuid.uuid4(),
            attempt_id=uuid.uuid4(),
            reference=QuestionReference(correct_option="B"),
        )

    monkeypatch.setattr(ask_student_module, "interrupt", fake_interrupt)
    monkeypatch.setattr(ask_student_module, "record_ask_student", fake_record)
    tool_obj = cast(_ToolWithFunc, make_ask_student())

    result = tool_obj.func(question=_question(), runtime=_runtime())

    assert result == "学生答案：b\n参考答案：B"
    assert captured["payload"] == {
        "type": "ask_student",
        "mode": "single_choice",
        "question": "TTL=1 时第一台路由器会做什么？",
        "options": ["直接转发", "回 ICMP Time Exceeded"],
        "answer": {"correct_option": "B"},
    }
    assert captured["response_schema"] is AskStudentResume
    assert captured["answer"] == "b"
    assert captured["context"] == ToolContext(
        user_id="user-1",
        thread_id="thread-1",
        tool_call_id="call-1",
    )


def test_tool_recorder_failure_does_not_break_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.ask_student as ask_student_module

    monkeypatch.setattr(
        ask_student_module,
        "interrupt",
        lambda payload, *, response_schema: AskStudentResume(answer="因为要匹配原始探测包"),
    )

    def fake_record(
        *,
        context: ToolContext,
        question: Question,
        answer: str,
    ) -> AskStudentRecordResponse:
        raise QuestionBankError("题库服务不可用")

    monkeypatch.setattr(ask_student_module, "record_ask_student", fake_record)

    result = cast(_ToolWithFunc, make_ask_student()).func(
        question=AskQuestion(
            mode="short_answer",
            stem="为什么？",
            reference_answer="为了匹配原始探测包",
            primary_knowledge_point_id="4.4.1",
        ),
        runtime=_runtime(),
    )

    assert "学生答案：因为要匹配原始探测包" in result
    assert "参考答案：为了匹配原始探测包" in result
    assert "题库记录失败" in result


def test_resume_strips_answer_and_has_no_note() -> None:
    resume = AskStudentResume(answer="  b  ")
    assert resume.answer == "b"
    assert "note" not in AskStudentResume.model_fields


def test_resume_rejects_blank_answer() -> None:
    with pytest.raises(ValidationError):
        AskStudentResume(answer="   ")


def test_tool_context_requires_auth() -> None:
    runtime = SimpleNamespace(config={"configurable": {}}, tool_call_id="call-1")

    with pytest.raises(KeyError):
        tool_context(cast(ToolRuntime, runtime))


def test_tool_context_requires_tool_call_id() -> None:
    runtime = SimpleNamespace(
        config={"configurable": {"langgraph_auth_user_id": "u", "thread_id": "t"}},
        tool_call_id=None,
    )

    with pytest.raises(RuntimeError, match="缺少 tool_call_id"):
        tool_context(cast(ToolRuntime, runtime))
