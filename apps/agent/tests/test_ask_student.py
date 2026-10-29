from collections.abc import Callable
from types import SimpleNamespace
from typing import Protocol, cast

import pytest
from pydantic import ValidationError

from agent.infra.question_bank_api import AskStudentRecordResult
from agent.tools.ask_student import make_ask_student
from agent.tools.schemas.ask_student import (
    AskStudentAnswer,
    AskStudentPayload,
    AskStudentResume,
    GeneratedQuestion,
    TeachAskStudentToolInput,
)


class _ToolWithFunc(Protocol):
    func: Callable[..., str]


class _FakeRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.error: Exception | None = None

    def record_ask_student(
        self,
        *,
        user_id: str,
        thread_id: str | None,
        tool_call_id: str,
        question: GeneratedQuestion,
        answer: str,
    ) -> AskStudentRecordResult:
        self.calls.append(
            {
                "user_id": user_id,
                "thread_id": thread_id,
                "tool_call_id": tool_call_id,
                "question": question,
                "answer": answer,
            }
        )
        if self.error is not None:
            raise self.error
        return AskStudentRecordResult(
            question_id="question-1",
            attempt_id="attempt-1",
            correct_option=question.correct_option,
            reference_answer=question.reference_answer,
        )


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


def test_single_choice_payload() -> None:
    payload = AskStudentPayload(
        mode="single_choice",
        question="TTL=1 时第一台路由器会做什么？",
        options=[
            "A. 直接转发给目标",
            "B. 丢弃并回 ICMP Time Exceeded",
            "C. 回 ICMP Port Unreachable",
        ],
        answer=AskStudentAnswer(correct_option="B"),
    )

    assert payload.type == "ask_student"
    assert payload.mode == "single_choice"
    assert payload.options is not None
    assert len(payload.options) == 3
    assert payload.answer.correct_option == "B"
    assert payload.model_dump(mode="json", exclude_none=True)["type"] == "ask_student"


def test_short_answer_payload_can_have_empty_answer() -> None:
    payload = AskStudentPayload(
        mode="short_answer",
        question="解释一下",
        answer=AskStudentAnswer(),
    )

    assert payload.model_dump(mode="json", exclude_none=True)["answer"] == {}


def test_short_answer_payload() -> None:
    payload = AskStudentPayload(
        mode="short_answer",
        question="为什么 ICMP 错误包要带内层 IPv4 + UDP？",
        placeholder="用一句话说明原因",
        answer=AskStudentAnswer(
            reference_answer="为了让接收方知道是哪个上层协议/端口触发的错误。"
        ),
    )

    assert payload.options is None
    assert payload.placeholder == "用一句话说明原因"
    assert payload.answer.reference_answer is not None


def test_short_answer_rejects_options() -> None:
    with pytest.raises(ValidationError, match="short_answer 不能提供 options") as exc_info:
        TeachAskStudentToolInput(
            mode="short_answer",
            question="解释一下",
            options=["A. 错误"],
            primary_knowledge_point_id="5.8.2",
        )

    assert any(error["loc"] == ("options",) for error in exc_info.value.errors())


def test_single_choice_requires_options() -> None:
    with pytest.raises(ValidationError, match="必须提供 2–6 个 options") as exc_info:
        TeachAskStudentToolInput(
            mode="single_choice",
            question="选一个",
            primary_knowledge_point_id="5.8.2",
            correct_option="A",
        )

    assert any(error["loc"] == ("options",) for error in exc_info.value.errors())


def test_single_choice_options_without_letter_prefix_return_actionable_error() -> None:
    """回归：模型把纯选项内容传给 options 时，错误必须指向 options 且说明原因。"""
    with pytest.raises(ValidationError) as exc_info:
        TeachAskStudentToolInput(
            mode="single_choice",
            question=(
                "教材 2.1 开头先说明物理层要「屏蔽掉传输媒体和通信手段的差异」，"
                "然后才给出物理层的主要任务。\n\n"
                "下面哪一项属于物理层的**主要任务**？"
            ),
            options=[
                "规定与传输媒体接口有关的机械、电气、功能和过程特性",
                "决定这次布线使用双绞线、同轴电缆还是光纤",
                "规定某种传输媒体的材料成分、屏蔽方式与最大传输距离",
                "比较各种传输媒体的价格并选出最经济的一种",
            ],
            correct_option="A",
            primary_knowledge_point_id="2.1",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("options",) for error in errors)
    assert "必须以 A. 开头" in str(exc_info.value)


def test_single_choice_rejects_out_of_order_letters() -> None:
    with pytest.raises(ValidationError, match="字母必须是 B"):
        TeachAskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=["A. 一", "C. 三"],
            correct_option="A",
            primary_knowledge_point_id="5.8.2",
        )


def test_single_choice_rejects_duplicate_bodies() -> None:
    with pytest.raises(ValidationError, match="选项内容重复"):
        TeachAskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=["A. 同一个", "B. 同一个"],
            correct_option="A",
            primary_knowledge_point_id="5.8.2",
        )


def test_single_choice_rejects_too_many_options() -> None:
    with pytest.raises(ValidationError, match="必须提供 2–6 个 options"):
        TeachAskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=[f"{letter}. 选项" for letter in "ABCDEFG"],
            correct_option="A",
            primary_knowledge_point_id="5.8.2",
        )


def test_question_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        TeachAskStudentToolInput(
            mode="short_answer",
            question="   ",
            primary_knowledge_point_id="5.8.2",
        )


def test_single_choice_requires_correct_option() -> None:
    with pytest.raises(ValidationError, match="必须提供 correct_option") as exc_info:
        TeachAskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=["A. 一", "B. 二"],
            primary_knowledge_point_id="5.8.2",
        )

    assert any(
        error["loc"] == ("correct_option",) for error in exc_info.value.errors()
    )


def test_single_choice_rejects_reference_answer() -> None:
    with pytest.raises(ValidationError, match="reference_answer 必须省略"):
        TeachAskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=["A. 一", "B. 二"],
            correct_option="A",
            reference_answer="A 是对的",
            primary_knowledge_point_id="5.8.2",
        )


def test_knowledge_points_are_validated() -> None:
    with pytest.raises(ValidationError, match="辅知识点最多 3 个"):
        TeachAskStudentToolInput(
            mode="short_answer",
            question="问题",
            primary_knowledge_point_id="5.8",
            secondary_knowledge_point_ids=["5.8.1", "5.8.2", "5.8.3", "5.9.1"],
        )

    with pytest.raises(ValidationError, match="不能包含主知识点"):
        TeachAskStudentToolInput(
            mode="short_answer",
            question="问题",
            primary_knowledge_point_id="5.8",
            secondary_knowledge_point_ids=["5.8"],
        )


def test_resume_strips_answer_and_has_no_note() -> None:
    resume = AskStudentResume(answer="  b  ")
    assert resume.answer == "b"
    assert "note" not in AskStudentResume.model_fields


def test_resume_rejects_blank_answer() -> None:
    with pytest.raises(ValidationError):
        AskStudentResume(answer="   ")


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

    monkeypatch.setattr(ask_student_module, "interrupt", fake_interrupt)
    recorder = _FakeRecorder()
    tool_obj = cast(_ToolWithFunc, make_ask_student(recorder=recorder))

    result = tool_obj.func(
        mode="single_choice",
        question="TTL=1 时会发生什么？",
        options=["A. 直接转发", "B. 回 ICMP Time Exceeded"],
        primary_knowledge_point_id="4.2.5",
        secondary_knowledge_point_ids=["4.4.1"],
        correct_option="B",
        runtime=_runtime(),
    )

    assert result == "学生答案：b\n参考答案：B"
    assert captured["payload"] == {
        "type": "ask_student",
        "mode": "single_choice",
        "question": "TTL=1 时会发生什么？",
        "options": ["A. 直接转发", "B. 回 ICMP Time Exceeded"],
        "answer": {"correct_option": "B"},
    }
    assert captured["response_schema"] is AskStudentResume
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["user_id"] == "user-1"
    assert call["thread_id"] == "thread-1"
    assert call["tool_call_id"] == "call-1"
    assert call["answer"] == "b"
    generated = cast(GeneratedQuestion, call["question"])
    assert generated.mode == "single_choice"
    assert generated.primary_knowledge_point_id == "4.2.5"


def test_tool_does_not_validate_single_choice_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.ask_student as ask_student_module

    monkeypatch.setattr(
        ask_student_module,
        "interrupt",
        lambda payload, *, response_schema: AskStudentResume(answer="不会"),
    )
    recorder = _FakeRecorder()
    tool_obj = cast(_ToolWithFunc, make_ask_student(recorder=recorder))

    result = tool_obj.func(
        mode="single_choice",
        question="选一个",
        options=["A. 一", "B. 二"],
        primary_knowledge_point_id="5.8.2",
        correct_option="A",
        runtime=_runtime(),
    )

    assert result == "学生答案：不会\n参考答案：A"
    assert recorder.calls[0]["answer"] == "不会"


def test_tool_recorder_failure_does_not_break_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agent.tools.ask_student as ask_student_module

    monkeypatch.setattr(
        ask_student_module,
        "interrupt",
        lambda payload, *, response_schema: AskStudentResume(answer="因为要匹配原始探测包"),
    )
    recorder = _FakeRecorder()
    recorder.error = RuntimeError("boom")
    tool_obj = cast(_ToolWithFunc, make_ask_student(recorder=recorder))

    result = tool_obj.func(
        mode="short_answer",
        question="为什么？",
        primary_knowledge_point_id="4.4.1",
        reference_answer="为了匹配原始探测包",
        runtime=_runtime(),
    )

    assert "学生答案：因为要匹配原始探测包" in result
    assert "参考答案：为了匹配原始探测包" in result
    assert "题库记录失败" in result


def test_tool_short_answer_payload_contains_reference_answer(
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
        return AskStudentResume(answer="因为要匹配原始探测包")

    monkeypatch.setattr(ask_student_module, "interrupt", fake_interrupt)
    tool_obj = cast(_ToolWithFunc, make_ask_student(recorder=_FakeRecorder()))

    tool_obj.func(
        mode="short_answer",
        question="为什么？",
        primary_knowledge_point_id="4.4.1",
        reference_answer="为了匹配原始探测包",
        runtime=_runtime(),
    )

    assert captured["payload"] == {
        "type": "ask_student",
        "mode": "short_answer",
        "question": "为什么？",
        "answer": {"reference_answer": "为了匹配原始探测包"},
    }
