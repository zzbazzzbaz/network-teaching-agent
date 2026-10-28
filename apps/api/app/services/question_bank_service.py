from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas.question_bank import (
    AskStudentRecordResponse,
    KnowledgePointRef,
    KnowledgePointsResponse,
    QuestionDetail,
    QuestionDetailResponse,
    QuestionInput,
    QuestionReference,
    QuestionSearchItem,
    QuestionType,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableError,
)
from app.core.knowledge_points import (
    get_knowledge_point,
    has_knowledge_point_prefix,
    knowledge_point_title,
    knowledge_points_payload,
    validate_knowledge_points,
)
from app.core.pagination import PageRequest, PageResult
from app.models.question import Question, QuestionAttempt
from app.repositories.question_repository import question_repository

_PREFIX_PATTERN = re.compile(r"^\d+(?:\.\d+)*$")


def _stem_preview(stem: str) -> str:
    return re.sub(r"\s+", " ", stem).strip()[:160]


def _reference(payload: QuestionInput) -> QuestionReference:
    return QuestionReference(
        correct_option=payload.correct_option,
        reference_answer=payload.reference_answer,
    )


def _same_question(question: Question, payload: QuestionInput) -> bool:
    return (
        question.question_type == payload.question_type
        and question.stem == payload.stem
        and question.options == payload.options
        and question.correct_option == payload.correct_option
        and question.reference_answer == payload.reference_answer
        and question.primary_knowledge_point_id == payload.primary_knowledge_point_id
        and question.secondary_knowledge_point_ids
        == payload.secondary_knowledge_point_ids
    )


def _validate(payload: QuestionInput) -> None:
    validate_knowledge_points(
        payload.primary_knowledge_point_id,
        payload.secondary_knowledge_point_ids,
    )


class QuestionBankService:
    def create_question(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        payload: QuestionInput,
    ) -> Question:
        _validate(payload)
        try:
            question = question_repository.create_question(
                session,
                owner_id=user_id,
                payload=payload,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        session.refresh(question)
        return question

    def get_detail(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> QuestionDetailResponse:
        question = question_repository.get_question(session, question_id)
        if question is None or (
            question.owner_id is not None and question.owner_id != user_id
        ):
            raise NotFoundError("题目不存在")

        last_attempt_at = None
        if question.owner_id is not None:
            last_attempt_at = question_repository.last_attempt_times(
                session,
                user_id=user_id,
                question_ids=[question.question_id],
            ).get(question.question_id)
        return self._to_detail(question, last_attempt_at=last_attempt_at)

    def update_question(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
        payload: QuestionInput,
    ) -> QuestionDetailResponse:
        question = self._get_owned_private_question(
            session,
            user_id=user_id,
            question_id=question_id,
            action="编辑",
        )
        _validate(payload)
        try:
            question_repository.update_question(session, question, payload=payload)
            session.commit()
        except Exception:
            session.rollback()
            raise
        session.refresh(question)

        last_attempt_at = question_repository.last_attempt_times(
            session,
            user_id=user_id,
            question_ids=[question.question_id],
        ).get(question.question_id)
        return self._to_detail(question, last_attempt_at=last_attempt_at)

    def delete_question(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> None:
        question = self._get_owned_private_question(
            session,
            user_id=user_id,
            question_id=question_id,
            action="删除",
        )
        if question_repository.count_attempts(session, question.question_id) > 0:
            raise ConflictError("题目已有作答记录，不能删除")
        try:
            question_repository.delete_question(session, question)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ConflictError("题目已有作答记录，不能删除") from None
        except Exception:
            session.rollback()
            raise

    def knowledge_points(self) -> KnowledgePointsResponse:
        return KnowledgePointsResponse.model_validate(knowledge_points_payload())

    def validate_public_search_filters(
        self,
        *,
        knowledge_point_id: str | None,
        knowledge_point_prefix: str | None,
    ) -> None:
        if knowledge_point_id is not None and get_knowledge_point(knowledge_point_id) is None:
            raise UnprocessableError(f"知识点不存在：{knowledge_point_id}")
        if knowledge_point_prefix is not None and not has_knowledge_point_prefix(
            knowledge_point_prefix
        ):
            raise UnprocessableError(f"知识点前缀不存在：{knowledge_point_prefix}")

    def _get_owned_private_question(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
        action: str,
    ) -> Question:
        question = question_repository.get_question(session, question_id)
        if question is None:
            raise NotFoundError("题目不存在")
        if question.owner_id is None:
            raise ForbiddenError(f"公共题不能{action}")
        if question.owner_id != user_id:
            raise NotFoundError("题目不存在")
        return question

    def record_ask_student(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        thread_id: str | None,
        tool_call_id: str,
        payload: QuestionInput,
        answer: str,
    ) -> AskStudentRecordResponse:
        _validate(payload)
        answer = answer.strip()

        existing = question_repository.get_attempt_by_tool_call(
            session,
            user_id=user_id,
            tool_call_id=tool_call_id,
        )
        if existing is not None:
            return self._existing_response(session, existing, payload, answer)

        try:
            question = question_repository.create_question(
                session,
                owner_id=user_id,
                payload=payload,
            )
            attempt = question_repository.create_attempt(
                session,
                user_id=user_id,
                question_id=question.question_id,
                thread_id=thread_id,
                tool_call_id=tool_call_id,
                answer_text=answer,
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = question_repository.get_attempt_by_tool_call(
                session,
                user_id=user_id,
                tool_call_id=tool_call_id,
            )
            if existing is None:
                raise
            return self._existing_response(session, existing, payload, answer)
        except Exception:
            session.rollback()
            raise

        return AskStudentRecordResponse(
            question_id=question.question_id,
            attempt_id=attempt.attempt_id,
            reference=_reference(payload),
        )

    def _existing_response(
        self,
        session: Session,
        attempt: QuestionAttempt,
        payload: QuestionInput,
        answer: str,
    ) -> AskStudentRecordResponse:
        question = question_repository.get_question(session, attempt.question_id)
        if (
            question is None
            or question.owner_id != attempt.user_id
            or not _same_question(question, payload)
            or attempt.answer_text != answer
        ):
            raise ConflictError("同一个 tool_call_id 的题目或答案不一致")
        return AskStudentRecordResponse(
            question_id=question.question_id,
            attempt_id=attempt.attempt_id,
            reference=_reference(payload),
        )

    def search(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        scope: str,
        query: str | None,
        question_type: QuestionType | None,
        knowledge_point_id: str | None,
        knowledge_point_prefix: str | None,
        page: PageRequest,
        detail: QuestionDetail,
    ) -> PageResult[QuestionSearchItem]:
        if knowledge_point_prefix and not _PREFIX_PATTERN.fullmatch(knowledge_point_prefix):
            raise UnprocessableError("knowledge_point_prefix 必须使用目录编号，如 5 或 5.8")

        if detail == "full" and page.limit > 3:
            page = PageRequest(limit=3, offset=page.offset)

        result = question_repository.search(
            session,
            user_id=user_id,
            scope=scope,
            query=query,
            question_type=question_type,
            knowledge_point_id=knowledge_point_id,
            knowledge_point_prefix=knowledge_point_prefix,
            page=page,
        )

        last_attempts: dict[uuid.UUID, datetime] = {}
        if scope != "public":
            mine_ids = [q.question_id for q in result.items if q.owner_id is not None]
            last_attempts = question_repository.last_attempt_times(
                session,
                user_id=user_id,
                question_ids=mine_ids,
            )

        items = [
            self._to_item(
                question,
                detail=detail,
                last_attempt_at=last_attempts.get(question.question_id),
            )
            for question in result.items
        ]
        return PageResult(
            items=items,
            total=result.total,
            limit=result.limit,
            offset=result.offset,
        )

    def search_for_student(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        scope: str,
        query: str | None,
        question_type: QuestionType | None,
        knowledge_point_id: str | None,
        knowledge_point_prefix: str | None,
        page: PageRequest,
    ) -> PageResult[QuestionSearchItem]:
        self.validate_public_search_filters(
            knowledge_point_id=knowledge_point_id,
            knowledge_point_prefix=knowledge_point_prefix,
        )
        return self.search(
            session,
            user_id=user_id,
            scope=scope,
            query=query,
            question_type=question_type,
            knowledge_point_id=knowledge_point_id,
            knowledge_point_prefix=knowledge_point_prefix,
            page=page,
            detail="summary",
        )

    def _to_item(
        self,
        question: Question,
        *,
        detail: QuestionDetail,
        last_attempt_at: datetime | None,
    ) -> QuestionSearchItem:
        secondary = [
            KnowledgePointRef(id=kp_id, title=knowledge_point_title(kp_id))
            for kp_id in question.secondary_knowledge_point_ids
        ]
        primary = KnowledgePointRef(
            id=question.primary_knowledge_point_id,
            title=knowledge_point_title(question.primary_knowledge_point_id),
        )
        return QuestionSearchItem(
            question_id=question.question_id,
            origin="public" if question.owner_id is None else "mine",
            question_type=cast(QuestionType, question.question_type),
            stem_preview=_stem_preview(question.stem),
            stem=question.stem if detail == "full" else None,
            options=question.options if detail == "full" else None,
            correct_option=question.correct_option if detail == "full" else None,
            reference_answer=question.reference_answer if detail == "full" else None,
            primary_knowledge_point=primary,
            secondary_knowledge_points=secondary,
            last_attempt_at=last_attempt_at,
        )

    def _to_detail(
        self,
        question: Question,
        *,
        last_attempt_at: datetime | None,
    ) -> QuestionDetailResponse:
        secondary = [
            KnowledgePointRef(id=kp_id, title=knowledge_point_title(kp_id))
            for kp_id in question.secondary_knowledge_point_ids
        ]
        return QuestionDetailResponse(
            question_id=question.question_id,
            origin="public" if question.owner_id is None else "mine",
            question_type=cast(QuestionType, question.question_type),
            stem=question.stem,
            options=question.options,
            correct_option=question.correct_option,
            reference_answer=question.reference_answer,
            primary_knowledge_point=KnowledgePointRef(
                id=question.primary_knowledge_point_id,
                title=knowledge_point_title(question.primary_knowledge_point_id),
            ),
            secondary_knowledge_points=secondary,
            last_attempt_at=last_attempt_at,
        )

    def replace_public_questions(
        self,
        session: Session,
        *,
        questions: list[QuestionInput],
        dry_run: bool,
    ) -> tuple[int, int]:
        if question_repository.has_public_attempts(session):
            raise UnprocessableError("公共题存在作答记录，拒绝整体替换")
        for payload in questions:
            _validate(payload)

        if dry_run:
            return question_repository.count_public_questions(session), len(questions)

        try:
            deleted = question_repository.delete_public_questions(session)
            for payload in questions:
                question_repository.create_question(
                    session,
                    owner_id=None,
                    payload=payload,
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        return deleted, len(questions)


question_bank_service = QuestionBankService()
