from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('single_choice', 'short_answer')",
            name="ck_questions_type",
        ),
        CheckConstraint("char_length(stem) <= 4000", name="ck_questions_stem_length"),
        CheckConstraint(
            "secondary_knowledge_point_ids IS NOT NULL "
            "AND jsonb_typeof(secondary_knowledge_point_ids) = 'array' "
            "AND jsonb_array_length(secondary_knowledge_point_ids) <= 3",
            name="ck_questions_secondary_knowledge_points",
        ),
        CheckConstraint(
            "(question_type = 'single_choice' "
            "AND options IS NOT NULL "
            "AND jsonb_typeof(options) = 'array' "
            "AND jsonb_array_length(options) BETWEEN 2 AND 6 "
            "AND correct_option IS NOT NULL "
            "AND reference_answer IS NULL) "
            "OR (question_type = 'short_answer' "
            "AND options IS NULL "
            "AND correct_option IS NULL)",
            name="ck_questions_type_fields",
        ),
        CheckConstraint(
            "correct_option IS NULL OR correct_option IN ('A', 'B', 'C', 'D', 'E', 'F')",
            name="ck_questions_correct_option",
        ),
        Index("ix_questions_owner_created_at", "owner_id", text("created_at DESC")),
        Index("ix_questions_deleted_at", "deleted_at"),
        Index("ix_questions_primary_knowledge_point_id", "primary_knowledge_point_id"),
        Index(
            "ix_questions_secondary_knowledge_points",
            "secondary_knowledge_point_ids",
            postgresql_using="gin",
        ),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    question_type: Mapped[str] = mapped_column(String(16), nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str] | None] = mapped_column(
        JSONB(none_as_null=True),
        nullable=True,
    )
    correct_option: Mapped[str | None] = mapped_column(String(1), nullable=True)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_knowledge_point_id: Mapped[str] = mapped_column(String(16), nullable=False)
    secondary_knowledge_point_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    __table_args__ = (
        CheckConstraint("char_length(answer_text) <= 2000", name="ck_attempts_answer_length"),
        CheckConstraint(
            "note IS NULL OR char_length(note) <= 4000",
            name="ck_attempts_note_length",
        ),
        Index(
            "uq_question_attempts_user_tool_call",
            "user_id",
            "tool_call_id",
            unique=True,
            postgresql_where=text("tool_call_id IS NOT NULL"),
        ),
        Index("ix_question_attempts_user_created_at", "user_id", text("created_at DESC")),
        Index(
            "ix_question_attempts_user_question_created_at",
            "user_id",
            "question_id",
            text("created_at DESC"),
        ),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.question_id", ondelete="RESTRICT"),
        nullable=False,
    )
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
