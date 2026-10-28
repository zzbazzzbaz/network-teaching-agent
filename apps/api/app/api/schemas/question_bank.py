from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

from app.api.schemas.base import ApiRequest, ApiResponse
from app.api.schemas.pagination import Page, PageQuery

QuestionType = Literal["single_choice", "short_answer"]
QuestionScope = Literal["all", "public", "mine"]
QuestionDetail = Literal["summary", "full"]

_OPTION_PATTERN = re.compile(r"^(?P<letter>[A-F])[.、)）]\s*(?P<body>.+)$")


class QuestionPageQuery(PageQuery):
    limit: int = Field(default=10, ge=1, le=20)


class QuestionSearchQuery(QuestionPageQuery):
    scope: QuestionScope = "all"
    query: str | None = Field(default=None, min_length=1, max_length=100)
    question_type: QuestionType | None = None
    knowledge_point_id: str | None = Field(default=None, max_length=16)
    knowledge_point_prefix: str | None = Field(default=None, max_length=16)


class InternalQuestionSearchQuery(QuestionSearchQuery):
    detail: QuestionDetail = "summary"


class QuestionInput(ApiRequest):
    question_type: QuestionType
    stem: str = Field(min_length=1, max_length=4000)
    options: list[str] | None = None
    correct_option: str | None = None
    reference_answer: str | None = Field(default=None, max_length=8000)
    primary_knowledge_point_id: str = Field(min_length=1, max_length=16)
    secondary_knowledge_point_ids: list[str] = Field(default_factory=list)

    @field_validator("stem", "primary_knowledge_point_id", mode="before")
    @classmethod
    def _strip_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("reference_answer", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
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

    @field_validator("options", mode="before")
    @classmethod
    def _strip_options(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value

    @field_validator("secondary_knowledge_point_ids", mode="before")
    @classmethod
    def _strip_secondary(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def _validate_type_fields(self) -> Self:
        if len(self.secondary_knowledge_point_ids) > 3:
            raise ValueError("辅知识点最多 3 个")
        if len(set(self.secondary_knowledge_point_ids)) != len(
            self.secondary_knowledge_point_ids
        ):
            raise ValueError("辅知识点不能重复")
        if self.primary_knowledge_point_id in self.secondary_knowledge_point_ids:
            raise ValueError("辅知识点不能包含主知识点")

        if self.question_type == "single_choice":
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
            if self.correct_option is None:
                raise ValueError("single_choice 必须提供 correct_option")
            if self.correct_option not in {
                chr(ord("A") + index) for index in range(len(self.options))
            }:
                raise ValueError("correct_option 必须匹配选项字母")
            if self.reference_answer is not None:
                raise ValueError("single_choice 的 reference_answer 必须为 NULL")
        else:
            if self.options is not None:
                raise ValueError("short_answer 不能提供 options")
            if self.correct_option is not None:
                raise ValueError("short_answer 不能提供 correct_option")
        return self


class AskStudentRecordRequest(ApiRequest):
    thread_id: str | None = Field(default=None, max_length=64)
    tool_call_id: str = Field(min_length=1, max_length=128)
    question: QuestionInput
    answer: str = Field(min_length=1, max_length=2000)

    @field_validator("thread_id", "tool_call_id", "answer", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class QuestionCreateRequest(QuestionInput):
    pass


class QuestionUpdateRequest(QuestionInput):
    pass


class QuestionReference(ApiResponse):
    correct_option: str | None
    reference_answer: str | None


class AskStudentRecordResponse(ApiResponse):
    question_id: UUID
    attempt_id: UUID
    reference: QuestionReference


class QuestionCreateResponse(ApiResponse):
    question_id: UUID


class KnowledgePointRef(ApiResponse):
    id: str
    title: str


class QuestionSearchItem(ApiResponse):
    question_id: UUID
    origin: Literal["public", "mine"]
    question_type: QuestionType
    stem_preview: str
    stem: str | None = None
    options: list[str] | None = None
    correct_option: str | None = None
    reference_answer: str | None = None
    primary_knowledge_point: KnowledgePointRef
    secondary_knowledge_points: list[KnowledgePointRef]
    last_attempt_at: datetime | None = None

    @model_serializer(mode="wrap")
    def _drop_summary_answer_fields(
        self,
        handler: SerializerFunctionWrapHandler,
    ) -> dict[str, object]:
        data = handler(self)
        if self.stem is None:
            for key in ("stem", "options", "correct_option", "reference_answer"):
                data.pop(key, None)
        return data


class QuestionSearchResponse(Page[QuestionSearchItem]):
    pass


class QuestionDetailResponse(ApiResponse):
    question_id: UUID
    origin: Literal["public", "mine"]
    question_type: QuestionType
    stem: str
    options: list[str] | None = None
    correct_option: str | None = None
    reference_answer: str | None = None
    primary_knowledge_point: KnowledgePointRef
    secondary_knowledge_points: list[KnowledgePointRef]
    last_attempt_at: datetime | None = None


class KnowledgePointNode(ApiResponse):
    id: str
    title: str
    parent_id: str | None
    level: int


class KnowledgePointsResponse(ApiResponse):
    version: int
    course: str
    nodes: list[KnowledgePointNode]
