from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from agent.tools.schemas.ask_student import (
    _KNOWLEDGE_POINT_PATTERN,
    _validate_options,
)

QuestionType = Literal["single_choice", "short_answer"]
QuestionScope = Literal["all", "public", "mine"]
QuestionDetail = Literal["summary", "full"]


class SearchQuestionsInput(BaseModel):
    scope: QuestionScope = Field(
        default="all",
        description="all 同时搜公共题库和我的题库；public 只搜公共题；mine 只搜我的题库。",
    )
    query: str | None = Field(default=None, max_length=100, description="题干模糊搜索。")
    question_type: QuestionType | None = Field(default=None, description="按题型筛选。")
    knowledge_point_id: str | None = Field(
        default=None,
        max_length=16,
        description="精确匹配主/辅知识点，使用教材目录编号，如 5.8.2。",
    )
    knowledge_point_prefix: str | None = Field(
        default=None,
        max_length=16,
        description="按目录前缀匹配主/辅知识点，如 5 或 5.8。",
    )
    limit: int = Field(default=10, ge=1, le=20)
    offset: int = Field(default=0, ge=0)
    detail: QuestionDetail = Field(
        default="summary",
        description="summary 不返回答案；full 最多 3 条，含答案/参考答案，仅用于讲解。",
    )

    @field_validator("query", "knowledge_point_id", "knowledge_point_prefix", mode="before")
    @classmethod
    def _strip_optional(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def _validate_search(self) -> Self:
        if self.knowledge_point_id and not _KNOWLEDGE_POINT_PATTERN.fullmatch(
            self.knowledge_point_id
        ):
            raise ValueError("knowledge_point_id 必须使用教材目录编号，如 5.8.2")
        if self.knowledge_point_prefix and not _KNOWLEDGE_POINT_PATTERN.fullmatch(
            self.knowledge_point_prefix
        ):
            raise ValueError("knowledge_point_prefix 必须使用教材目录编号，如 5.8")
        if self.detail == "full" and self.limit > 3:
            self.limit = 3
        return self


class SaveQuestionInput(BaseModel):
    question_type: QuestionType
    stem: str = Field(min_length=1, max_length=4000)
    options: list[str] | None = None
    correct_option: str | None = None
    reference_answer: str | None = Field(default=None, max_length=8000)
    primary_knowledge_point_id: str = Field(min_length=1, max_length=16)
    secondary_knowledge_point_ids: list[str] = Field(default_factory=list)

    @field_validator("stem", "primary_knowledge_point_id", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("reference_answer", mode="before")
    @classmethod
    def _strip_optional(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("correct_option", mode="before")
    @classmethod
    def _normalize_correct_option(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            return value or None
        return value

    @field_validator("options", "secondary_knowledge_point_ids", mode="before")
    @classmethod
    def _strip_list(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def _validate_question(self) -> Self:
        if not _KNOWLEDGE_POINT_PATTERN.fullmatch(self.primary_knowledge_point_id):
            raise ValueError("primary_knowledge_point_id 必须使用教材目录编号，如 5.8.2")
        secondary = self.secondary_knowledge_point_ids
        if len(secondary) > 3:
            raise ValueError("辅知识点最多 3 个")
        if len(set(secondary)) != len(secondary):
            raise ValueError("辅知识点不能重复")
        if self.primary_knowledge_point_id in secondary:
            raise ValueError("辅知识点不能包含主知识点")
        for knowledge_point_id in secondary:
            if not _KNOWLEDGE_POINT_PATTERN.fullmatch(knowledge_point_id):
                raise ValueError("辅知识点必须使用教材目录编号，如 5.8.1")

        if self.question_type == "single_choice":
            if self.options is None:
                raise ValueError("single_choice 必须提供 2–6 个 options")
            _validate_options(self.options)
            if self.correct_option is None:
                raise ValueError("single_choice 必须提供 correct_option")
            valid_letters = {chr(ord("A") + index) for index in range(len(self.options))}
            if self.correct_option not in valid_letters:
                raise ValueError("correct_option 必须匹配选项字母")
            if self.reference_answer is not None:
                raise ValueError("single_choice 的 reference_answer 必须省略")
        else:
            if self.options is not None:
                raise ValueError("short_answer 不能提供 options")
            if self.correct_option is not None:
                raise ValueError("short_answer 不能提供 correct_option")
        return self
