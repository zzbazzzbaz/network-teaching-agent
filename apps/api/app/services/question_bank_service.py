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
    QuestionDetail,
    QuestionInput,
    QuestionReference,
    QuestionSearchItem,
    QuestionSearchResponse,
    QuestionType,
)
from app.core.exceptions import ConflictError, UnprocessableError
from app.core.knowledge_points import (
    knowledge_point_title,
    validate_knowledge_points,
)
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
        limit: int,
        offset: int,
        detail: QuestionDetail,
    ) -> QuestionSearchResponse:
        if knowledge_point_prefix and not _PREFIX_PATTERN.fullmatch(knowledge_point_prefix):
            raise UnprocessableError("knowledge_point_prefix 必须使用目录编号，如 5 或 5.8")

        if detail == "full" and limit > 3:
            limit = 3

        questions, total = question_repository.search(
            session,
            user_id=user_id,
            scope=scope,
            query=query,
            question_type=question_type,
            knowledge_point_id=knowledge_point_id,
            knowledge_point_prefix=knowledge_point_prefix,
            limit=limit,
            offset=offset,
        )

        last_attempts: dict[uuid.UUID, datetime] = {}
        if scope != "public":
            mine_ids = [q.question_id for q in questions if q.owner_id is not None]
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
            for question in questions
        ]
        return QuestionSearchResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
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
