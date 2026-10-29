from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import interrupt

from agent.infra.question_bank_api import QuestionBankError, record_ask_student
from agent.runtime.context import tool_context
from agent.tools.schemas.ask_student import AskStudentInput, AskStudentResume
from agent.tools.schemas.question import AskQuestion

_DESCRIPTION = (
    "向学生提出检查题或引导题，并等待学生作答。"
    "question.mode 为 single_choice（单选）或 short_answer（简答）；"
    "options 是纯文本，不要自带 A./B. 字母；correct_option 用 A–F 字母。"
    "学生作答后工具会自动把题目和答案保存到题库。"
    "调用后本次运行会暂停，直到客户端提交答案。"
    "出题规范见 /skills/teaching/ask-student/SKILL.md。"
)


def _format_result(
    answer: str,
    *,
    reference: str | None,
    warning: str | None = None,
) -> str:
    lines = [f"学生答案：{answer}"]
    if reference:
        lines.append(f"参考答案：{reference}")
    if warning:
        lines.append(f"（题库记录失败，不影响继续：{warning}）")
    return "\n".join(lines)


def make_ask_student() -> BaseTool:
    @tool(args_schema=AskStudentInput, description=_DESCRIPTION)
    def ask_student(*, question: AskQuestion, runtime: ToolRuntime) -> str:
        answer = interrupt(
            question.to_payload(),
            response_schema=AskStudentResume,
        ).answer

        reference = question.correct_option or question.reference_answer
        try:
            record = record_ask_student(
                context=tool_context(runtime),
                question=question,
                answer=answer,
            )
        except QuestionBankError as e:
            return _format_result(answer, reference=reference, warning=str(e))
        return _format_result(
            answer,
            reference=record.reference.reference_answer
            or record.reference.correct_option,
        )

    return ask_student
