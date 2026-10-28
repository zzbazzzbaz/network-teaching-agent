from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from agent.core.config import get_settings
from agent.tools.schemas.ask_student import GeneratedQuestion
from agent.tools.schemas.question_bank import SaveQuestionInput, SearchQuestionsInput


class QuestionBankApiError(RuntimeError):
    """题库 API 不可用或返回错误。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class QuestionBankAuthError(QuestionBankApiError):
    """当前运行没有可用的用户身份。"""


@dataclass(frozen=True)
class AskStudentRecordResult:
    question_id: str
    attempt_id: str
    correct_option: str | None
    reference_answer: str | None


class AskStudentRecorder(Protocol):
    def record_ask_student(
        self,
        *,
        user_id: str,
        thread_id: str | None,
        tool_call_id: str,
        question: GeneratedQuestion,
        answer: str,
    ) -> AskStudentRecordResult: ...


def _headers(user_id: str) -> dict[str, str]:
    settings = get_settings()
    return {
        "X-Internal-Token": settings.agent_internal_token,
        "X-User-Id": user_id,
    }


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return ""


def _request(
    method: str,
    path: str,
    *,
    user_id: str,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    base_url = settings.agent_api_base_url.rstrip("/")
    try:
        response = httpx.request(
            method,
            f"{base_url}{path}",
            params=params,
            json=json,
            headers=_headers(user_id),
            timeout=timeout if timeout is not None else settings.agent_api_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as e:
        detail = _detail(e.response)
        suffix = f"：{detail}" if detail else ""
        raise QuestionBankApiError(
            f"题库服务返回 {e.response.status_code}{suffix}",
            status_code=e.response.status_code,
        ) from e
    except (httpx.HTTPError, ValueError) as e:
        raise QuestionBankApiError("题库服务暂不可用，请稍后重试") from e

    if not isinstance(payload, dict):
        raise QuestionBankApiError("题库服务返回格式错误")
    return payload


def _configurable(config: Mapping[str, Any]) -> dict[str, Any]:
    value = config.get("configurable")
    return value if isinstance(value, dict) else {}


def user_id_from_config(config: Mapping[str, Any]) -> str:
    user_id = _configurable(config).get("langgraph_auth_user_id")
    if not isinstance(user_id, str) or not user_id:
        raise QuestionBankAuthError("未认证，无法访问题库")
    return user_id


def thread_id_from_config(config: Mapping[str, Any]) -> str | None:
    configurable = _configurable(config)
    thread_id = configurable.get("thread_id")
    if isinstance(thread_id, str) and thread_id:
        return thread_id
    metadata = config.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("thread_id")
        if isinstance(value, str) and value:
            return value
    return None


def tool_call_id_from_config(config: Mapping[str, Any]) -> str | None:
    metadata = config.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("tool_call_id")
        if isinstance(value, str) and value:
            return value
    return None


def _record_request(
    *,
    user_id: str,
    thread_id: str | None,
    tool_call_id: str,
    question: GeneratedQuestion,
    answer: str,
) -> AskStudentRecordResult:
    settings = get_settings()
    payload = _request(
        "POST",
        "/internal/question-bank/ask-student/record",
        user_id=user_id,
        json={
            "thread_id": thread_id,
            "tool_call_id": tool_call_id,
            "question": {
                "question_type": question.mode,
                "stem": question.question,
                "options": question.options,
                "correct_option": question.correct_option,
                "reference_answer": question.reference_answer,
                "primary_knowledge_point_id": question.primary_knowledge_point_id,
                "secondary_knowledge_point_ids": question.secondary_knowledge_point_ids,
            },
            "answer": answer,
        },
        timeout=min(settings.agent_api_timeout_seconds, 5),
    )
    question_id = payload.get("question_id")
    attempt_id = payload.get("attempt_id")
    reference = payload.get("reference")
    if not isinstance(question_id, str) or not isinstance(attempt_id, str):
        raise QuestionBankApiError("题库服务未返回 question_id / attempt_id")
    if not isinstance(reference, dict):
        raise QuestionBankApiError("题库服务未返回参考答案")
    correct_option = reference.get("correct_option")
    reference_answer = reference.get("reference_answer")
    return AskStudentRecordResult(
        question_id=question_id,
        attempt_id=attempt_id,
        correct_option=correct_option if isinstance(correct_option, str) else None,
        reference_answer=reference_answer if isinstance(reference_answer, str) else None,
    )


class QuestionBankRecorder:
    """真实 API recorder；网络/5xx 最多重试一次，4xx 不重试。"""

    def record_ask_student(
        self,
        *,
        user_id: str,
        thread_id: str | None,
        tool_call_id: str,
        question: GeneratedQuestion,
        answer: str,
    ) -> AskStudentRecordResult:
        try:
            return _record_request(
                user_id=user_id,
                thread_id=thread_id,
                tool_call_id=tool_call_id,
                question=question,
                answer=answer,
            )
        except QuestionBankApiError as e:
            if e.status_code is not None and e.status_code < 500:
                raise
        return _record_request(
            user_id=user_id,
            thread_id=thread_id,
            tool_call_id=tool_call_id,
            question=question,
            answer=answer,
        )


def search_questions(user_id: str, query: SearchQuestionsInput) -> dict[str, Any]:
    params: dict[str, Any] = {
        "scope": query.scope,
        "limit": query.limit,
        "offset": query.offset,
        "detail": query.detail,
    }
    if query.query is not None:
        params["query"] = query.query
    if query.question_type is not None:
        params["question_type"] = query.question_type
    if query.knowledge_point_id is not None:
        params["knowledge_point_id"] = query.knowledge_point_id
    if query.knowledge_point_prefix is not None:
        params["knowledge_point_prefix"] = query.knowledge_point_prefix
    return _request(
        "GET",
        "/internal/question-bank/questions",
        user_id=user_id,
        params=params,
    )


def save_question(user_id: str, question: SaveQuestionInput) -> dict[str, Any]:
    return _request(
        "POST",
        "/internal/question-bank/questions",
        user_id=user_id,
        json={
            "question_type": question.question_type,
            "stem": question.stem,
            "options": question.options,
            "correct_option": question.correct_option,
            "reference_answer": question.reference_answer,
            "primary_knowledge_point_id": question.primary_knowledge_point_id,
            "secondary_knowledge_point_ids": question.secondary_knowledge_point_ids,
        },
    )
