from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import InternalUserDep, SessionDep
from app.api.schemas.question_bank import (
    AskStudentRecordRequest,
    AskStudentRecordResponse,
    InternalQuestionSearchQuery,
    QuestionCreateRequest,
    QuestionCreateResponse,
    QuestionSearchResponse,
)
from app.core.pagination import PageRequest
from app.services.question_bank_service import question_bank_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal-question-bank"], include_in_schema=False)


@router.post("/ask-student/record", response_model=AskStudentRecordResponse)
def record_ask_student(
    body: AskStudentRecordRequest,
    session: SessionDep,
    user_id: InternalUserDep,
) -> AskStudentRecordResponse:
    result = question_bank_service.record_ask_student(
        session,
        user_id=user_id,
        thread_id=body.thread_id,
        tool_call_id=body.tool_call_id,
        payload=body.question,
        answer=body.answer,
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
    params: Annotated[InternalQuestionSearchQuery, Query()],
    session: SessionDep,
    user_id: InternalUserDep,
) -> QuestionSearchResponse:
    page = PageRequest(limit=params.limit, offset=params.offset)
    result = question_bank_service.search(
        session,
        user_id=user_id,
        scope=params.scope,
        query=params.query,
        question_type=params.question_type,
        knowledge_point_id=params.knowledge_point_id,
        knowledge_point_prefix=params.knowledge_point_prefix,
        page=page,
        detail=params.detail,
    )
    logger.info(
        "题库检索 user_id=%s scope=%s count=%s",
        user_id,
        params.scope,
        len(result.items),
    )
    return QuestionSearchResponse(
        items=result.items,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.post(
    "/questions",
    response_model=QuestionCreateResponse,
    status_code=201,
)
def create_question(
    body: QuestionCreateRequest,
    session: SessionDep,
    user_id: InternalUserDep,
) -> QuestionCreateResponse:
    question = question_bank_service.create_question(
        session,
        user_id=user_id,
        payload=body,
    )
    logger.info(
        "题库私有题已创建 user_id=%s question_id=%s",
        user_id,
        question.question_id,
    )
    return QuestionCreateResponse(question_id=question.question_id)
