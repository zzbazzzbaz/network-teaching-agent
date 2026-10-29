import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

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
            "提问模式。single_choice 为单选题，必须提供 2–6 个自带 A.–F. 字母前缀的选项；"
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
        # single_choice 漏传 options 时也要走校验，给出可读错误。
        validate_default=True,
        description=(
            "单选题选项，2–6 个。每个字符串都必须自带字母前缀，按顺序写成 "
            "\"A. …\"、\"B. …\"（也接受 A、、A)、A））；工具不会自动补字母。"
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

    @field_validator("options", mode="after")
    @classmethod
    def _validate_options_for_mode(
        cls, value: list[str] | None, info: ValidationInfo
    ) -> list[str] | None:
        # 放在 field_validator 里，ValidationError.loc 才会是 ("options",)；
        # model_validator 的 loc 是 ()，会被 LangGraph 过滤成空错误。
        mode = info.data.get("mode")
        if mode == "single_choice":
            if value is None:
                raise ValueError("single_choice 必须提供 2–6 个 options")
            _validate_options(value)
        elif mode == "short_answer" and value:
            raise ValueError("short_answer 不能提供 options")
        return value


class AskStudentAnswer(BaseModel):
    correct_option: str | None = None
    reference_answer: str | None = None


class AskStudentPayload(_QuestionDisplayFields):
    """中断时发送给前端的 payload，包含答案供前端本地隐藏。"""

    type: Literal["ask_student"] = "ask_student"
    answer: AskStudentAnswer

    @field_validator("answer", mode="after")
    @classmethod
    def _validate_answer(
        cls, value: AskStudentAnswer, info: ValidationInfo
    ) -> AskStudentAnswer:
        mode = info.data.get("mode")
        if mode == "single_choice":
            if value.correct_option is None:
                raise ValueError("single_choice 的 answer 必须包含 correct_option")
            if value.reference_answer is not None:
                raise ValueError("single_choice 的 answer 不能包含 reference_answer")
        elif mode == "short_answer" and value.correct_option is not None:
            raise ValueError("short_answer 的 answer 不能包含 correct_option")
        return value


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
        # single_choice 漏传 correct_option 时也要走校验，给出可读错误。
        validate_default=True,
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

    @field_validator("primary_knowledge_point_id", mode="after")
    @classmethod
    def _validate_primary_knowledge_point(cls, value: str) -> str:
        if not _KNOWLEDGE_POINT_PATTERN.fullmatch(value):
            raise ValueError("primary_knowledge_point_id 必须使用教材目录编号，如 5.8.2")
        return value

    @field_validator("correct_option", mode="before")
    @classmethod
    def _normalize_correct_option(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            return value or None
        return value

    @field_validator("correct_option", mode="after")
    @classmethod
    def _validate_correct_option(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        mode = info.data.get("mode")
        if mode == "single_choice":
            if value is None:
                raise ValueError("single_choice 必须提供 correct_option")
            options = info.data.get("options")
            if isinstance(options, list):
                valid_letters = {
                    chr(ord("A") + index) for index in range(len(options))
                }
                if value not in valid_letters:
                    raise ValueError("correct_option 必须匹配选项字母")
        elif mode == "short_answer" and value is not None:
            raise ValueError("short_answer 不能提供 correct_option")
        return value

    @field_validator("reference_answer", mode="before")
    @classmethod
    def _strip_reference(cls, value: object) -> object:
        return _strip_optional_text(value)

    @field_validator("reference_answer", mode="after")
    @classmethod
    def _validate_reference_answer(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        if info.data.get("mode") == "single_choice" and value is not None:
            raise ValueError("single_choice 的 reference_answer 必须省略")
        return value

    @field_validator("secondary_knowledge_point_ids", mode="before")
    @classmethod
    def _strip_secondary(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value

    @field_validator("secondary_knowledge_point_ids", mode="after")
    @classmethod
    def _validate_secondary_knowledge_points(
        cls, value: list[str] | None, info: ValidationInfo
    ) -> list[str] | None:
        secondary = value or []
        if len(secondary) > 3:
            raise ValueError("辅知识点最多 3 个")
        if len(set(secondary)) != len(secondary):
            raise ValueError("辅知识点不能重复")
        primary = info.data.get("primary_knowledge_point_id")
        if isinstance(primary, str) and primary in secondary:
            raise ValueError("辅知识点不能包含主知识点")
        for knowledge_point_id in secondary:
            if not _KNOWLEDGE_POINT_PATTERN.fullmatch(knowledge_point_id):
                raise ValueError("辅知识点必须使用教材目录编号，如 5.8.1")
        return value


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
