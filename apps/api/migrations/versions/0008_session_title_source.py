"""add session title source

Revision ID: 0008_session_title_source
Revises: 0007_question_soft_delete
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_session_title_source"
down_revision: str | Sequence[str] | None = "0007_question_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("title_source", sa.String(length=16), nullable=True),
    )
    op.execute(
        """
        UPDATE sessions
        SET title_source = CASE
            WHEN title = '新会话' THEN 'default'
            ELSE 'user'
        END
        """
    )
    op.alter_column(
        "sessions",
        "title_source",
        nullable=False,
        server_default=sa.text("'default'"),
    )
    op.create_check_constraint(
        "ck_sessions_title_source",
        "sessions",
        "title_source IN ('default', 'auto', 'user')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sessions_title_source",
        "sessions",
        type_="check",
    )
    op.drop_column("sessions", "title_source")
