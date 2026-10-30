from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.schemas.question_bank import QuestionInput
from app.core.pagination import PageRequest, PageResult
from app.models.question import Question, QuestionAttempt


def _search_conditions(
    *,
    user_id: uuid.UUID,
    scope: str,
    query: str | None,
    question_type: str | None,
    knowledge_point_id: str | None = None,
    knowledge_point_prefix: str | None = None,
    knowledge_point_match: str = "any",
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [Question.deleted_at.is_(None)]
    if scope == "public":
        conditions.append(Question.owner_id.is_(None))
    elif scope == "mine":
        conditions.append(Question.owner_id == user_id)
    else:
        conditions.append(
            or_(Question.owner_id.is_(None), Question.owner_id == user_id)
        )

    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(Question.stem.ilike(f"%{escaped}%", escape="\\"))
    if question_type:
        conditions.append(Question.question_type == question_type)

    if knowledge_point_id:
        if knowledge_point_match == "primary":
            conditions.append(
                Question.primary_knowledge_point_id == knowledge_point_id
            )
        else:
            conditions.append(
                or_(
                    Question.primary_knowledge_point_id == knowledge_point_id,
                    Question.secondary_knowledge_point_ids.contains([knowledge_point_id]),
                )
            )

    if knowledge_point_prefix:
        prefix_like = f"{knowledge_point_prefix}.%"
        primary_matches = or_(
            Question.primary_knowledge_point_id == knowledge_point_prefix,
            Question.primary_knowledge_point_id.like(prefix_like),
        )
        if knowledge_point_match == "primary":
            conditions.append(primary_matches)
        else:
            conditions.append(
                or_(
                    primary_matches,
                    text(
                        "EXISTS ("
                        "SELECT 1 FROM jsonb_array_elements_text("
                        "questions.secondary_knowledge_point_ids"
                        ") AS secondary_kp "
                        "WHERE secondary_kp = :kp_prefix "
                        "OR secondary_kp LIKE :kp_prefix_like"
                        ")"
                    ).bindparams(
                        kp_prefix=knowledge_point_prefix,
                        kp_prefix_like=prefix_like,
                    ),
                )
            )
    return conditions


class QuestionRepository:
    def create_question(
        self,
        session: Session,
        *,
        owner_id: uuid.UUID | None,
        payload: QuestionInput,
        import_key: str | None = None,
    ) -> Question:
        question = Question(
            owner_id=owner_id,
            question_type=payload.question_type,
            stem=payload.stem,
            options=payload.options,
            correct_option=payload.correct_option,
            reference_answer=payload.reference_answer,
            primary_knowledge_point_id=payload.primary_knowledge_point_id,
            secondary_knowledge_point_ids=payload.secondary_knowledge_point_ids,
            import_key=import_key,
        )
        session.add(question)
        session.flush()
        return question

    def get_question(self, session: Session, question_id: uuid.UUID) -> Question | None:
        return session.scalar(
            select(Question).where(
                Question.question_id == question_id,
                Question.deleted_at.is_(None),
            )
        )

    def get_by_import_key(
        self,
        session: Session,
        *,
        owner_id: uuid.UUID,
        import_key: str,
    ) -> Question | None:
        return session.scalar(
            select(Question).where(
                Question.owner_id == owner_id,
                Question.import_key == import_key,
                Question.deleted_at.is_(None),
            )
        )

    def list_attempts(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
        page: PageRequest,
    ) -> PageResult[QuestionAttempt]:
        conditions = [
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.question_id == question_id,
        ]
        base = select(QuestionAttempt).where(*conditions)
        total = session.scalar(
            select(func.count()).select_from(base.order_by(None).subquery())
        )
        items = list(
            session.scalars(
                base.order_by(
                    QuestionAttempt.created_at.desc(),
                    QuestionAttempt.attempt_id.desc(),
                )
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        return PageResult(
            items=items,
            total=int(total or 0),
            limit=page.limit,
            offset=page.offset,
        )

    def update_question(
        self,
        session: Session,
        question: Question,
        *,
        payload: QuestionInput,
    ) -> Question:
        question.question_type = payload.question_type
        question.stem = payload.stem
        question.options = payload.options
        question.correct_option = payload.correct_option
        question.reference_answer = payload.reference_answer
        question.primary_knowledge_point_id = payload.primary_knowledge_point_id
        question.secondary_knowledge_point_ids = payload.secondary_knowledge_point_ids
        session.flush()
        return question

    def count_attempts(self, session: Session, question_id: uuid.UUID) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(QuestionAttempt)
                .where(QuestionAttempt.question_id == question_id)
            )
            or 0
        )

    def soft_delete_question(self, session: Session, question: Question) -> None:
        question.deleted_at = datetime.now(UTC)
        session.flush()

    def get_attempt_by_tool_call(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        tool_call_id: str,
    ) -> QuestionAttempt | None:
        return session.scalar(
            select(QuestionAttempt).where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.tool_call_id == tool_call_id,
            )
        )

    def create_attempt(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
        thread_id: str | None,
        tool_call_id: str,
        answer_text: str,
    ) -> QuestionAttempt:
        attempt = QuestionAttempt(
            user_id=user_id,
            question_id=question_id,
            thread_id=thread_id,
            tool_call_id=tool_call_id,
            answer_text=answer_text,
            note=None,
        )
        session.add(attempt)
        session.flush()
        return attempt

    def last_attempt_times(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        question_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, datetime]:
        if not question_ids:
            return {}
        rows = session.execute(
            select(QuestionAttempt.question_id, func.max(QuestionAttempt.created_at))
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.question_id.in_(question_ids),
            )
            .group_by(QuestionAttempt.question_id)
        ).all()
        return {question_id: created_at for question_id, created_at in rows}

    def search(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        scope: str,
        query: str | None,
        question_type: str | None,
        knowledge_point_id: str | None,
        knowledge_point_prefix: str | None,
        knowledge_point_match: str,
        page: PageRequest,
    ) -> PageResult[Question]:
        conditions = _search_conditions(
            user_id=user_id,
            scope=scope,
            query=query,
            question_type=question_type,
            knowledge_point_id=knowledge_point_id,
            knowledge_point_prefix=knowledge_point_prefix,
            knowledge_point_match=knowledge_point_match,
        )

        base = select(Question).where(*conditions)
        total = session.scalar(
            select(func.count()).select_from(base.order_by(None).subquery())
        )
        items = list(
            session.scalars(
                base.order_by(Question.created_at.desc(), Question.question_id.desc())
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        return PageResult(
            items=items,
            total=int(total or 0),
            limit=page.limit,
            offset=page.offset,
        )

    def count_by_primary_knowledge_point(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        query: str | None,
        question_type: str | None,
    ) -> list[tuple[bool, str, int]]:
        """返回 [(is_public, primary_knowledge_point_id, count)]。

        只聚合主知识点；公共题和我的题一次查出，all 由 service 相加。
        """
        conditions = _search_conditions(
            user_id=user_id,
            scope="all",
            query=query,
            question_type=question_type,
        )
        rows = session.execute(
            select(
                Question.owner_id.is_(None),
                Question.primary_knowledge_point_id,
                func.count(),
            )
            .where(*conditions)
            .group_by(
                Question.owner_id.is_(None),
                Question.primary_knowledge_point_id,
            )
        ).all()
        return [
            (bool(is_public), str(knowledge_point_id), int(count))
            for is_public, knowledge_point_id, count in rows
        ]

    def has_public_attempts(self, session: Session) -> bool:
        return (
            session.scalar(
                select(func.count())
                .select_from(QuestionAttempt)
                .join(Question, Question.question_id == QuestionAttempt.question_id)
                .where(Question.owner_id.is_(None))
            )
            or 0
        ) > 0

    def count_public_questions(self, session: Session) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(Question)
                .where(
                    Question.owner_id.is_(None),
                    Question.deleted_at.is_(None),
                )
            )
            or 0
        )

    def delete_public_questions(self, session: Session) -> int:
        deleted = self.count_public_questions(session)
        session.execute(delete(Question).where(Question.owner_id.is_(None)))
        return deleted


question_repository = QuestionRepository()
