from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import interrupt

from agent.infra.question_bank_api import QuestionBankError, record_ask_student
from agent.runtime.context import tool_context
from agent.tools.schemas.ask_student import AskStudentInput, AskStudentResume
from agent.tools.schemas.question import AskQuestion

_DESCRIPTION = (
    "向学生提出一道检查题并等待作答，用于确认理解、暴露误解、推动学生自己推导。"
    "一次只问一个主问题；出题前读 /skills/teaching/ask-question/SKILL.md。"
    "学生作答后，题目和答案会存入他的题库。"
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
