from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import interrupt

from agent.infra.question_bank_api import (
    AskStudentRecorder,
    QuestionBankApiError,
    QuestionBankAuthError,
    thread_id_from_config,
    tool_call_id_from_config,
    user_id_from_config,
)
from agent.tools.schemas.ask_student import (
    AskStudentAnswer,
    AskStudentMode,
    AskStudentPayload,
    AskStudentResume,
    GeneratedQuestion,
    TeachAskStudentToolInput,
)

_DESCRIPTION = (
    "向学生提出检查题或引导题，并等待学生作答。"
    "支持 single_choice（单选）和 short_answer（简答）；"
    "必须给出 primary_knowledge_point_id，单选还必须给出 correct_option。"
    "学生作答后工具会自动把题目和答案保存到题库。"
    "调用后本次运行会暂停，直到客户端提交答案。"
    "出题规范见 /skills/teaching/ask-student/SKILL.md。"
)


def _format_result(
    answer: str,
    *,
    correct_option: str | None,
    reference_answer: str | None,
    warning: str | None,
) -> str:
    lines = [f"学生答案：{answer}"]
    reference = reference_answer or correct_option
    if reference:
        lines.append(f"参考答案：{reference}")
    if warning:
        lines.append(f"（题库记录失败，不影响继续：{warning}）")
    return "\n".join(lines)


def make_ask_student(*, recorder: AskStudentRecorder) -> BaseTool:
    """teach_agent 专用：知识点 + 自动保存。"""

    @tool(args_schema=TeachAskStudentToolInput, description=_DESCRIPTION)
    def ask_student(
        *,
        mode: AskStudentMode,
        question: str,
        options: list[str] | None = None,
        placeholder: str | None = None,
        primary_knowledge_point_id: str,
        secondary_knowledge_point_ids: list[str] | None = None,
        correct_option: str | None = None,
        reference_answer: str | None = None,
        runtime: ToolRuntime,
    ) -> str:
        payload = AskStudentPayload(
            mode=mode,
            question=question,
            options=options if mode == "single_choice" else None,
            placeholder=placeholder if mode == "short_answer" else None,
            answer=AskStudentAnswer(
                correct_option=correct_option if mode == "single_choice" else None,
                reference_answer=reference_answer if mode == "short_answer" else None,
            ),
        )
        result = interrupt(
            payload.model_dump(mode="json", exclude_none=True),
            response_schema=AskStudentResume,
        )
        answer = result.answer

        generated = GeneratedQuestion(
            mode=mode,
            question=question,
            options=options if mode == "single_choice" else None,
            correct_option=correct_option if mode == "single_choice" else None,
            reference_answer=reference_answer if mode == "short_answer" else None,
            primary_knowledge_point_id=primary_knowledge_point_id,
            secondary_knowledge_point_ids=secondary_knowledge_point_ids or [],
        )

        warning: str | None = None
        try:
            user_id = user_id_from_config(runtime.config)
            tool_call_id = runtime.tool_call_id or tool_call_id_from_config(runtime.config)
            if not tool_call_id:
                raise QuestionBankAuthError("缺少 tool_call_id")
            record = recorder.record_ask_student(
                user_id=user_id,
                thread_id=thread_id_from_config(runtime.config),
                tool_call_id=tool_call_id,
                question=generated,
                answer=answer,
            )
        except QuestionBankApiError as e:
            warning = str(e)
        except Exception as e:  # 题库失败不能打断教学主线
            warning = f"题库记录失败（{type(e).__name__}）"
        else:
            return _format_result(
                answer,
                correct_option=record.correct_option,
                reference_answer=record.reference_answer,
                warning=None,
            )

        return _format_result(
            answer,
            correct_option=correct_option if mode == "single_choice" else None,
            reference_answer=reference_answer if mode == "short_answer" else None,
            warning=warning,
        )

    return ask_student
