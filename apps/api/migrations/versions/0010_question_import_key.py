"""add question import key

Revision ID: 0010_question_import_key
Revises: 0009_files
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_question_import_key"
down_revision: str | Sequence[str] | None = "0009_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("import_key", sa.String(length=160), nullable=True),
    )
    op.create_index(
        "uq_questions_owner_import_key",
        "questions",
        ["owner_id", "import_key"],
        unique=True,
        postgresql_where=sa.text(
            "import_key IS NOT NULL AND deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_questions_owner_import_key", table_name="questions")
    op.drop_column("questions", "import_key")
