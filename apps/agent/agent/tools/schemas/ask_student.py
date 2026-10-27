import re
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

AskStudentMode = Literal["single_choice", "short_answer"]

_OPTION_PATTERN = re.compile(r"^(?P<letter>[A-F])[.、)）]\s*(?P<body>.+)$")


class _AskStudentBase(BaseModel):
    mode: AskStudentMode = Field(
        description=(
            "提问模式。single_choice 为单选题，必须提供 2–6 个 A.–F. 选项；"
            "short_answer 为简答题，不提供选项。"
        )
    )
    question: str = Field(
        min_length=1,
        max_length=4000,
        description=(
            "题干，支持 Markdown。图表请使用 ```mermaid 代码块；不要把 raw HTML/SVG 放进题干。"
        ),
    )
    options: list[str] | None = Field(
        default=None,
        description=(
            "单选题选项，2–6 个，按顺序使用 A.、B. 等前缀；"
            "选项保持纯文本，不放 Markdown、图片或 Mermaid。简答题必须省略。"
        ),
    )
    placeholder: str | None = Field(
        default=None,
        max_length=200,
        description="简答题输入框占位符；单选题忽略。",
    )

    @field_validator("question", "placeholder", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("options", mode="before")
    @classmethod
    def _strip_options(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def _validate_mode_fields(self) -> Self:
        if self.mode == "single_choice":
            if self.options is None or not 2 <= len(self.options) <= 6:
                raise ValueError("single_choice 必须提供 2–6 个 options")

            bodies: set[str] = set()
            for index, option in enumerate(self.options):
                expected_letter = chr(ord("A") + index)
                match = _OPTION_PATTERN.fullmatch(option)
                if match is None:
                    raise ValueError(f"选项 {option!r} 必须以 {expected_letter}. 开头")
                if match.group("letter") != expected_letter:
                    raise ValueError(
                        f"选项 {option!r} 的字母必须是 {expected_letter}，并按 A、B、C… 顺序排列"
                    )

                body = match.group("body").strip()
                if body in bodies:
                    raise ValueError(f"选项内容重复：{body!r}")
                bodies.add(body)

        elif self.options:
            raise ValueError("short_answer 不能提供 options")

        return self


class AskStudentToolInput(_AskStudentBase):
    """ask_student 工具参数。"""


class AskStudentPayload(_AskStudentBase):
    """中断时发送给前端的 payload。"""

    type: Literal["ask_student"] = "ask_student"


class AskStudentResume(BaseModel):
    answer: str = Field(
        min_length=1,
        max_length=2000,
        description='学生答案。单选题传字母，例如 "B"；简答题传文本。',
    )

    @field_validator("answer", mode="before")
    @classmethod
    def _strip_answer(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value
