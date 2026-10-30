from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.dependencies import SessionDep, UserIdDep
from app.api.schemas.question_bank import (
    AttemptPageQuery,
    KnowledgePointCountsQuery,
    KnowledgePointCountsResponse,
    KnowledgePointsResponse,
    QuestionAttemptListResponse,
    QuestionCreateRequest,
    QuestionCreateResponse,
    QuestionDetailResponse,
    QuestionSearchQuery,
    QuestionSearchResponse,
    QuestionUpdateRequest,
)
from app.core.pagination import PageRequest
from app.services.question_bank_service import question_bank_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/question-bank", tags=["question-bank"])


@router.get(
    "/questions",
    response_model=QuestionSearchResponse,
    summary="搜索公共题库和我的题库",
)
def search_questions(
    params: Annotated[QuestionSearchQuery, Query()],
    session: SessionDep,
    user_id: UserIdDep,
) -> QuestionSearchResponse:
    page = PageRequest(limit=params.limit, offset=params.offset)
    result = question_bank_service.search_for_student(
        session,
        user_id=user_id,
        scope=params.scope,
        query=params.query,
        question_type=params.question_type,
        knowledge_point_id=params.knowledge_point_id,
        knowledge_point_prefix=params.knowledge_point_prefix,
        knowledge_point_match=params.knowledge_point_match,
        page=page,
    )
    return QuestionSearchResponse(
        items=result.items,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.get(
    "/questions/{question_id}",
    response_model=QuestionDetailResponse,
    summary="获取题目详情",
)
def get_question(
    question_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> QuestionDetailResponse:
    return question_bank_service.get_detail(
        session,
        user_id=user_id,
        question_id=question_id,
    )


@router.get(
    "/questions/{question_id}/attempts",
    response_model=QuestionAttemptListResponse,
    summary="获取我的作答记录",
)
def list_question_attempts(
    question_id: uuid.UUID,
    params: Annotated[AttemptPageQuery, Query()],
    session: SessionDep,
    user_id: UserIdDep,
) -> QuestionAttemptListResponse:
    page = PageRequest(limit=params.limit, offset=params.offset)
    result = question_bank_service.list_attempts(
        session,
        user_id=user_id,
        question_id=question_id,
        page=page,
    )
    return QuestionAttemptListResponse(
        items=result.items,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.get(
    "/knowledge-points/counts",
    response_model=KnowledgePointCountsResponse,
    summary="获取知识点题量统计",
)
def get_knowledge_point_counts(
    params: Annotated[KnowledgePointCountsQuery, Query()],
    session: SessionDep,
    user_id: UserIdDep,
) -> KnowledgePointCountsResponse:
    result = question_bank_service.knowledge_point_counts(
        session,
        user_id=user_id,
        query=params.query,
        question_type=params.question_type,
    )
    logger.info(
        "题库知识点统计 user_id=%s totals=%s has_query=%s question_type=%s",
        user_id,
        result.totals,
        params.query is not None,
        params.question_type,
    )
    return result


@router.get(
    "/knowledge-points",
    response_model=KnowledgePointsResponse,
    summary="获取知识点目录",
)
def get_knowledge_points(_user_id: UserIdDep) -> KnowledgePointsResponse:
    return question_bank_service.knowledge_points()


@router.post(
    "/questions",
    response_model=QuestionCreateResponse,
    status_code=201,
    summary="新增私有题",
)
def create_question(
    body: QuestionCreateRequest,
    session: SessionDep,
    user_id: UserIdDep,
) -> QuestionCreateResponse:
    question = question_bank_service.create_question(
        session,
        user_id=user_id,
        payload=body,
    )
    logger.info(
        "公开题库私有题已创建 user_id=%s question_id=%s",
        user_id,
        question.question_id,
    )
    return QuestionCreateResponse(question_id=question.question_id)


@router.put(
    "/questions/{question_id}",
    response_model=QuestionDetailResponse,
    summary="编辑私有题",
)
def update_question(
    question_id: uuid.UUID,
    body: QuestionUpdateRequest,
    session: SessionDep,
    user_id: UserIdDep,
) -> QuestionDetailResponse:
    return question_bank_service.update_question(
        session,
        user_id=user_id,
        question_id=question_id,
        payload=body,
    )


@router.delete("/questions/{question_id}", status_code=204, summary="删除私有题")
def delete_question(
    question_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> Response:
    question_bank_service.delete_question(
        session,
        user_id=user_id,
        question_id=question_id,
    )
    return Response(status_code=204)
