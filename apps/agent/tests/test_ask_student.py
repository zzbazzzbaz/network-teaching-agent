import pytest
from pydantic import ValidationError

from agent.tools.schemas.ask_student import (
    AskStudentPayload,
    AskStudentResume,
    AskStudentToolInput,
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
    )

    assert payload.type == "ask_student"
    assert payload.mode == "single_choice"
    assert payload.options is not None
    assert len(payload.options) == 3
    assert payload.model_dump(mode="json", exclude_none=True)["type"] == "ask_student"


def test_short_answer_payload() -> None:
    payload = AskStudentPayload(
        mode="short_answer",
        question="为什么 ICMP 错误包要带内层 IPv4 + UDP？",
        placeholder="用一句话说明原因",
    )

    assert payload.options is None
    assert payload.placeholder == "用一句话说明原因"


def test_short_answer_rejects_options() -> None:
    with pytest.raises(ValidationError, match="short_answer 不能提供 options"):
        AskStudentToolInput(
            mode="short_answer",
            question="解释一下",
            options=["A. 错误"],
        )


def test_single_choice_requires_options() -> None:
    with pytest.raises(ValidationError, match="必须提供 2–6 个 options"):
        AskStudentToolInput(
            mode="single_choice",
            question="选一个",
        )


def test_single_choice_rejects_out_of_order_letters() -> None:
    with pytest.raises(ValidationError, match="字母必须是 B"):
        AskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=["A. 一", "C. 三"],
        )


def test_single_choice_rejects_duplicate_bodies() -> None:
    with pytest.raises(ValidationError, match="选项内容重复"):
        AskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=["A. 同一个", "B. 同一个"],
        )


def test_single_choice_rejects_too_many_options() -> None:
    with pytest.raises(ValidationError, match="必须提供 2–6 个 options"):
        AskStudentToolInput(
            mode="single_choice",
            question="选一个",
            options=[f"{letter}. 选项" for letter in "ABCDEFG"],
        )


def test_question_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        AskStudentToolInput(
            mode="short_answer",
            question="   ",
        )


def test_resume_strips_answer() -> None:
    assert AskStudentResume(answer="  B  ").answer == "B"


def test_resume_rejects_blank_answer() -> None:
    with pytest.raises(ValidationError):
        AskStudentResume(answer="   ")


def test_tool_interrupt_payload_for_single_choice(
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
    tool_obj = ask_student_module.make_ask_student()

    result = tool_obj.invoke({
        "mode": "single_choice",
        "question": "TTL=1 时会发生什么？",
        "options": ["A. 直接转发", "B. 回 ICMP Time Exceeded"],
    })

    assert result == "学生答案：B"
    assert captured["payload"] == {
        "type": "ask_student",
        "mode": "single_choice",
        "question": "TTL=1 时会发生什么？",
        "options": ["A. 直接转发", "B. 回 ICMP Time Exceeded"],
    }
    assert captured["response_schema"] is AskStudentResume


def test_tool_interrupt_payload_for_short_answer(
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
        return AskStudentResume(answer="  因为要匹配原始探测包  ")

    monkeypatch.setattr(ask_student_module, "interrupt", fake_interrupt)
    tool_obj = ask_student_module.make_ask_student()

    result = tool_obj.invoke({
        "mode": "short_answer",
        "question": "为什么 ICMP 错误包要带内层包？",
        "placeholder": "用一句话说明",
    })

    assert result == "学生答案：因为要匹配原始探测包"
    assert captured["payload"] == {
        "type": "ask_student",
        "mode": "short_answer",
        "question": "为什么 ICMP 错误包要带内层包？",
        "placeholder": "用一句话说明",
    }
