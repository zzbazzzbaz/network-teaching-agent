from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

QuestionMode = Literal["single_choice", "short_answer"]


class Question(BaseModel):
    """题目草稿；options 是纯文本，字母由前端按顺序渲染。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    mode: QuestionMode = Field(
        description="single_choice 为单选题；short_answer 为简答题。"
    )
    stem: str = Field(min_length=1, max_length=4000, description="题干，支持 Markdown。")
    options: list[str] | None = Field(
        default=None,
        description=(
            "单选题选项，2–6 个纯文本，不要自带 A./B. 字母；"
            "前端会按顺序显示 A、B、C…。简答题省略。"
        ),
    )
    correct_option: str | None = Field(
        default=None,
        description="单选题正确选项字母（A–F）；简答题省略。",
    )
    reference_answer: str | None = Field(
        default=None,
        max_length=8000,
        description="简答题参考答案；单选题省略。",
    )
    primary_knowledge_point_id: str = Field(
        min_length=1,
        max_length=16,
        description="教材 00-toc.md 的目录编号，如 5.8.2 或 99。",
    )
    secondary_knowledge_point_ids: list[str] = Field(
        default_factory=list,
        description="辅知识点目录编号，最多 3 个；不能重复，也不能包含主知识点。",
    )

    @field_validator("correct_option", mode="before")
    @classmethod
    def _normalize_correct_option(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            return value or None
        return value


class AskQuestion(Question):
    """ask_student 展示前必须合法的题目。"""

    placeholder: str | None = Field(
        default=None,
        max_length=200,
        description="简答题输入框占位符；单选题忽略。",
    )

    @model_validator(mode="after")
    def _validate_for_ask(self) -> Self:
        if self.mode == "single_choice":
            if self.options is None or not 2 <= len(self.options) <= 6:
                raise ValueError("单选题必须提供 2–6 个选项")
            if any(not option for option in self.options):
                raise ValueError("选项内容不能为空")
            if len(set(self.options)) != len(self.options):
                raise ValueError("选项内容不能重复")
            valid_letters = {
                chr(ord("A") + index) for index in range(len(self.options))
            }
            if self.correct_option not in valid_letters:
                raise ValueError("correct_option 必须是选项字母之一")
            if self.reference_answer:
                raise ValueError("单选题不能提供 reference_answer")
        else:
            if self.options is not None:
                raise ValueError("简答题不能提供 options")
            if self.correct_option is not None:
                raise ValueError("简答题不能提供 correct_option")
        return self

    def to_payload(self) -> dict[str, object]:
        answer: dict[str, str] = {}
        if self.mode == "single_choice":
            if self.correct_option is not None:
                answer["correct_option"] = self.correct_option
        elif self.reference_answer:
            answer["reference_answer"] = self.reference_answer

        payload: dict[str, object] = {
            "type": "ask_student",
            "mode": self.mode,
            "question": self.stem,
            "answer": answer,
        }
        if self.options is not None:
            payload["options"] = self.options
        if self.mode == "short_answer" and self.placeholder:
            payload["placeholder"] = self.placeholder
        return payload
