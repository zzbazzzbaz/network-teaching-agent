from langchain_core.tools import BaseTool, tool
from langgraph.types import interrupt

from agent.tools.schemas.ask_student import (
    AskStudentMode,
    AskStudentPayload,
    AskStudentResume,
    AskStudentToolInput,
)

_DESCRIPTION = (
    "向学生提出检查题或引导题，并等待学生作答。"
    "支持 single_choice（单选）和 short_answer（简答）；"
    "调用后本次运行会暂停，直到客户端提交答案。"
    "出题规范见 /skills/common/ask-student/SKILL.md。"
)


def make_ask_student() -> BaseTool:
    @tool(args_schema=AskStudentToolInput, description=_DESCRIPTION)
    def ask_student(
        *,
        mode: AskStudentMode,
        question: str,
        options: list[str] | None = None,
        placeholder: str | None = None,
    ) -> str:
        payload = AskStudentPayload(
            mode=mode,
            question=question,
            options=options if mode == "single_choice" else None,
            placeholder=placeholder if mode == "short_answer" else None,
        )
        result = interrupt(
            payload.model_dump(mode="json", exclude_none=True),
            response_schema=AskStudentResume,
        )

        answer = result.answer
        if mode == "single_choice":
            answer = answer.upper()
            valid_letters = {
                option[0].upper()
                for option in (options or [])
                if option and option[0].upper() in "ABCDEF"
            }
            if answer not in valid_letters:
                return (
                    f"学生答案：{answer}（无效选项，有效选项：{'、'.join(sorted(valid_letters))}）"
                )

        return f"学生答案：{answer}"

    return ask_student
