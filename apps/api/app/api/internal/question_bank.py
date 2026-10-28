from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import InternalUserDep, SessionDep
from app.api.schemas.question_bank import (
    AskStudentRecordRequest,
    AskStudentRecordResponse,
    QuestionCreateRequest,
    QuestionCreateResponse,
    QuestionDetail,
    QuestionScope,
    QuestionSearchResponse,
    QuestionType,
)
from app.services.question_bank_service import question_bank_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal-question-bank"], include_in_schema=False)


@router.post("/ask-student/record", response_model=AskStudentRecordResponse)
def record_ask_student(
    payload: AskStudentRecordRequest,
    session: SessionDep,
    user_id: InternalUserDep,
) -> AskStudentRecordResponse:
    result = question_bank_service.record_ask_student(
        session,
        user_id=user_id,
        thread_id=payload.thread_id,
        tool_call_id=payload.tool_call_id,
        payload=payload.question,
        answer=payload.answer,
    )
    logger.info(
        "题库作答已记录 user_id=%s question_id=%s attempt_id=%s",
        user_id,
        result.question_id,
        result.attempt_id,
    )
    return result


@router.get("/questions", response_model=QuestionSearchResponse)
def search_questions(
    session: SessionDep,
    user_id: InternalUserDep,
    scope: QuestionScope = "all",
    query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    question_type: QuestionType | None = None,
    knowledge_point_id: Annotated[str | None, Query(max_length=16)] = None,
    knowledge_point_prefix: Annotated[str | None, Query(max_length=16)] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
    detail: QuestionDetail = "summary",
) -> QuestionSearchResponse:
    result = question_bank_service.search(
        session,
        user_id=user_id,
        scope=scope,
        query=query,
        question_type=question_type,
        knowledge_point_id=knowledge_point_id,
        knowledge_point_prefix=knowledge_point_prefix,
        limit=limit,
        offset=offset,
        detail=detail,
    )
    logger.info(
        "题库检索 user_id=%s scope=%s count=%s",
        user_id,
        scope,
        len(result.items),
    )
    return result


@router.post("/questions", response_model=QuestionCreateResponse)
def create_question(
    payload: QuestionCreateRequest,
    session: SessionDep,
    user_id: InternalUserDep,
) -> QuestionCreateResponse:
    question = question_bank_service.create_question(
        session,
        user_id=user_id,
        payload=payload,
    )
    logger.info(
        "题库私有题已创建 user_id=%s question_id=%s",
        user_id,
        question.question_id,
    )
    return QuestionCreateResponse(question_id=question.question_id)
