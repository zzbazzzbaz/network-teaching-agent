from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

import httpx
from pydantic import BaseModel

from agent.core.config import get_settings
from agent.runtime.context import ToolContext
from agent.tools.schemas.question import Question
from agent.tools.schemas.question_bank import SearchQuestionsInput


class QuestionBankError(RuntimeError):
    """题库 API 不可用或返回错误。"""


class KnowledgePointRef(BaseModel):
    id: str
    title: str


class QuestionReference(BaseModel):
    correct_option: str | None = None
    reference_answer: str | None = None


class AskStudentRecordResponse(BaseModel):
    question_id: UUID
    attempt_id: UUID
    reference: QuestionReference


class SearchItem(BaseModel):
    question_id: UUID
    origin: Literal["public", "mine"]
    question_type: Literal["single_choice", "short_answer"]
    stem_preview: str
    stem: str | None = None
    options: list[str] | None = None
    correct_option: str | None = None
    reference_answer: str | None = None
    primary_knowledge_point: KnowledgePointRef
    secondary_knowledge_points: list[KnowledgePointRef]
    last_attempt_at: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchItem]
    total: int
    limit: int
    offset: int


class QuestionDetail(BaseModel):
    question_id: UUID
    origin: Literal["public", "mine"]
    question_type: Literal["single_choice", "short_answer"]
    stem: str
    options: list[str] | None = None
    correct_option: str | None = None
    reference_answer: str | None = None
    primary_knowledge_point: KnowledgePointRef
    secondary_knowledge_points: list[KnowledgePointRef]
    last_attempt_at: str | None = None


class PracticeAttemptResponse(BaseModel):
    attempt_id: UUID
    question_id: UUID
    reference: QuestionReference


class SaveQuestionResponse(BaseModel):
    question_id: UUID


def _headers(context: ToolContext) -> dict[str, str]:
    settings = get_settings()
    return {
        "X-Internal-Token": settings.server.auth_token,
        "X-User-Id": context.user_id,
    }


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if not isinstance(item, dict):
                continue
            loc = ".".join(
                str(part)
                for part in item.get("loc", ())
                if part not in {"body", "query", "path"}
            )
            message = str(item.get("msg", ""))
            parts.append(f"{loc}: {message}" if loc else message)
        return "；".join(parts)
    return ""


def _request[T: BaseModel](
    method: str,
    path: str,
    *,
    context: ToolContext,
    response_model: type[T],
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> T:
    settings = get_settings()
    base_url = settings.server.api_base_url.rstrip("/")
    try:
        response = httpx.request(
            method,
            f"{base_url}{path}",
            params=params,
            json=json,
            headers=_headers(context),
            timeout=timeout if timeout is not None else settings.server.timeout_seconds,
        )
        response.raise_for_status()
        return response_model.model_validate(response.json())
    except httpx.HTTPStatusError as e:
        detail = _detail(e.response)
        suffix = f"：{detail}" if detail else ""
        raise QuestionBankError(f"题库服务返回 {e.response.status_code}{suffix}") from e
    except (httpx.HTTPError, ValueError) as e:
        raise QuestionBankError("题库服务暂不可用，请稍后重试") from e


def _question_path_id(question_id: str | UUID) -> str:
    """把外部传入的题目 ID 规范化为 UUID 字符串，避免路径穿越。"""
    try:
        return str(UUID(str(question_id)))
    except (TypeError, ValueError, AttributeError) as e:
        raise QuestionBankError("题目 ID 格式不正确") from e


def _question_payload(question: Question) -> dict[str, Any]:
    return {
        "question_type": question.mode,
        "stem": question.stem,
        "options": question.options,
        "correct_option": question.correct_option,
        "reference_answer": question.reference_answer,
        "primary_knowledge_point_id": question.primary_knowledge_point_id,
        "secondary_knowledge_point_ids": question.secondary_knowledge_point_ids,
    }


def record_ask_student(
    *,
    context: ToolContext,
    question: Question,
    answer: str,
) -> AskStudentRecordResponse:
    return _request(
        "POST",
        "/internal/question-bank/ask-student/record",
        context=context,
        json={
            "thread_id": context.thread_id,
            "tool_call_id": context.tool_call_id,
            "question": _question_payload(question),
            "answer": answer,
        },
        response_model=AskStudentRecordResponse,
        timeout=min(get_settings().server.timeout_seconds, 5),
    )


def search_questions(context: ToolContext, query: SearchQuestionsInput) -> SearchResponse:
    params: dict[str, Any] = {
        "scope": query.scope,
        "limit": query.limit,
        "offset": query.offset,
        "detail": query.detail,
    }
    if query.query:
        params["query"] = query.query
    if query.question_type:
        params["question_type"] = query.question_type
    if query.knowledge_point_id:
        params["knowledge_point_id"] = query.knowledge_point_id
    if query.knowledge_point_prefix:
        params["knowledge_point_prefix"] = query.knowledge_point_prefix
    return _request(
        "GET",
        "/internal/question-bank/questions",
        context=context,
        params=params,
        response_model=SearchResponse,
    )


def save_question(context: ToolContext, question: Question) -> SaveQuestionResponse:
    return create_question(context, question)


def create_question(
    context: ToolContext,
    question: Question,
    *,
    import_key: str | None = None,
) -> SaveQuestionResponse:
    payload = _question_payload(question)
    if import_key is not None:
        payload["import_key"] = import_key
    return _request(
        "POST",
        "/internal/question-bank/questions",
        context=context,
        json=payload,
        response_model=SaveQuestionResponse,
    )


def get_question(context: ToolContext, question_id: str | UUID) -> QuestionDetail:
    return _request(
        "GET",
        f"/internal/question-bank/questions/{_question_path_id(question_id)}",
        context=context,
        response_model=QuestionDetail,
    )


def record_practice_attempt(
    context: ToolContext,
    *,
    question_id: str | UUID,
    answer: str,
) -> PracticeAttemptResponse:
    return _request(
        "POST",
        f"/internal/question-bank/questions/{_question_path_id(question_id)}/attempts",
        context=context,
        json={
            "thread_id": context.thread_id,
            "tool_call_id": context.tool_call_id,
            "answer": answer,
        },
        response_model=PracticeAttemptResponse,
        timeout=min(get_settings().server.timeout_seconds, 5),
    )
