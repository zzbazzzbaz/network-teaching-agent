"""add question soft delete

Revision ID: 0007_question_soft_delete
Revises: 0006_plain_text_options
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_question_soft_delete"
down_revision: str | Sequence[str] | None = "0006_plain_text_options"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_questions_deleted_at", "questions", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_questions_deleted_at", table_name="questions")
    op.drop_column("questions", "deleted_at")
