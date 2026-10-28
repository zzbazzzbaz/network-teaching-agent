import re
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

AskStudentMode = Literal["single_choice", "short_answer"]

_OPTION_PATTERN = re.compile(r"^(?P<letter>[A-F])[.、)）]\s*(?P<body>.+)$")
_KNOWLEDGE_POINT_PATTERN = re.compile(r"^\d+(?:\.\d+)*$")


def _strip_optional_text(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _validate_options(options: list[str]) -> None:
    if not 2 <= len(options) <= 6:
        raise ValueError("single_choice 必须提供 2–6 个 options")

    bodies: set[str] = set()
    for index, option in enumerate(options):
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


class _QuestionDisplayFields(BaseModel):
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
            if self.options is None:
                raise ValueError("single_choice 必须提供 2–6 个 options")
            _validate_options(self.options)
        elif self.options:
            raise ValueError("short_answer 不能提供 options")
        return self


class AskStudentPayload(_QuestionDisplayFields):
    """中断时发送给前端的 payload，不含答案和知识点。"""

    type: Literal["ask_student"] = "ask_student"


class TeachAskStudentToolInput(_QuestionDisplayFields):
    """teach_agent 的 ask_student 工具参数。"""

    primary_knowledge_point_id: str = Field(
        min_length=1,
        max_length=16,
        description="主知识点 ID，必须使用教材 00-toc.md 的目录编号，如 5.8.2 或 99。",
    )
    secondary_knowledge_point_ids: list[str] | None = Field(
        default=None,
        description="辅知识点目录编号，最多 3 个；不能重复，也不能包含主知识点。",
    )
    correct_option: str | None = Field(
        default=None,
        description="单选题正确答案字母（A–F）；简答题必须省略。",
    )
    reference_answer: str | None = Field(
        default=None,
        max_length=8000,
        description="简答题参考答案；单选题必须省略。",
    )

    @field_validator("primary_knowledge_point_id", mode="before")
    @classmethod
    def _strip_knowledge_point(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("correct_option", mode="before")
    @classmethod
    def _normalize_correct_option(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            return value or None
        return value

    @field_validator("reference_answer", mode="before")
    @classmethod
    def _strip_reference(cls, value: object) -> object:
        return _strip_optional_text(value)

    @field_validator("secondary_knowledge_point_ids", mode="before")
    @classmethod
    def _strip_secondary(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def _validate_question_fields(self) -> Self:
        if not _KNOWLEDGE_POINT_PATTERN.fullmatch(self.primary_knowledge_point_id):
            raise ValueError("primary_knowledge_point_id 必须使用教材目录编号，如 5.8.2")
        secondary = self.secondary_knowledge_point_ids or []
        if len(secondary) > 3:
            raise ValueError("辅知识点最多 3 个")
        if len(set(secondary)) != len(secondary):
            raise ValueError("辅知识点不能重复")
        if self.primary_knowledge_point_id in secondary:
            raise ValueError("辅知识点不能包含主知识点")
        for knowledge_point_id in secondary:
            if not _KNOWLEDGE_POINT_PATTERN.fullmatch(knowledge_point_id):
                raise ValueError("辅知识点必须使用教材目录编号，如 5.8.1")

        if self.mode == "single_choice":
            if self.correct_option is None:
                raise ValueError("single_choice 必须提供 correct_option")
            if self.options is None:
                raise ValueError("single_choice 必须提供 2–6 个 options")
            valid_letters = {chr(ord("A") + index) for index in range(len(self.options))}
            if self.correct_option not in valid_letters:
                raise ValueError("correct_option 必须匹配选项字母")
            if self.reference_answer is not None:
                raise ValueError("single_choice 的 reference_answer 必须省略")
        else:
            if self.correct_option is not None:
                raise ValueError("short_answer 不能提供 correct_option")
        return self


class GeneratedQuestion(BaseModel):
    """recorder 发送给 API 的结构化题目。"""

    mode: AskStudentMode
    question: str = Field(min_length=1, max_length=4000)
    options: list[str] | None = None
    correct_option: str | None = None
    reference_answer: str | None = None
    primary_knowledge_point_id: str = Field(min_length=1, max_length=16)
    secondary_knowledge_point_ids: list[str] = Field(default_factory=list)


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
