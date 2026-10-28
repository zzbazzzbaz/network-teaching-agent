"""add question bank

Revision ID: 0004_question_bank
Revises: 0003_sandbox_lifecycle
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_question_bank"
down_revision: str | Sequence[str] | None = "0003_sandbox_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("question_type", sa.String(length=16), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correct_option", sa.String(length=1), nullable=True),
        sa.Column("reference_answer", sa.Text(), nullable=True),
        sa.Column("primary_knowledge_point_id", sa.String(length=16), nullable=False),
        sa.Column(
            "secondary_knowledge_point_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "question_type IN ('single_choice', 'short_answer')",
            name="ck_questions_type",
        ),
        sa.CheckConstraint("char_length(stem) <= 4000", name="ck_questions_stem_length"),
        sa.CheckConstraint(
            "secondary_knowledge_point_ids IS NOT NULL "
            "AND jsonb_typeof(secondary_knowledge_point_ids) = 'array' "
            "AND jsonb_array_length(secondary_knowledge_point_ids) <= 3",
            name="ck_questions_secondary_knowledge_points",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "correct_option IS NULL OR correct_option IN ('A', 'B', 'C', 'D', 'E', 'F')",
            name="ck_questions_correct_option",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id"),
    )
    op.create_index(
        "ix_questions_owner_created_at",
        "questions",
        ["owner_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_questions_primary_knowledge_point_id",
        "questions",
        ["primary_knowledge_point_id"],
    )
    op.create_index(
        "ix_questions_secondary_knowledge_points",
        "questions",
        ["secondary_knowledge_point_ids"],
        postgresql_using="gin",
    )

    op.create_table(
        "question_attempts",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=True),
        sa.Column("tool_call_id", sa.String(length=128), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("char_length(answer_text) <= 2000", name="ck_attempts_answer_length"),
        sa.CheckConstraint(
            "note IS NULL OR char_length(note) <= 4000",
            name="ck_attempts_note_length",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.question_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("attempt_id"),
    )
    op.create_index(
        "uq_question_attempts_user_tool_call",
        "question_attempts",
        ["user_id", "tool_call_id"],
        unique=True,
        postgresql_where=sa.text("tool_call_id IS NOT NULL"),
    )
    op.create_index(
        "ix_question_attempts_user_created_at",
        "question_attempts",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_question_attempts_user_question_created_at",
        "question_attempts",
        ["user_id", "question_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_question_attempts_user_question_created_at",
        table_name="question_attempts",
    )
    op.drop_index(
        "ix_question_attempts_user_created_at",
        table_name="question_attempts",
    )
    op.drop_index(
        "uq_question_attempts_user_tool_call",
        table_name="question_attempts",
    )
    op.drop_table("question_attempts")

    op.drop_index("ix_questions_secondary_knowledge_points", table_name="questions")
    op.drop_index("ix_questions_primary_knowledge_point_id", table_name="questions")
    op.drop_index("ix_questions_owner_created_at", table_name="questions")
    op.drop_table("questions")
