"""add session agent binding

Revision ID: 0005_session_agent
Revises: 0004_question_bank
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_session_agent"
down_revision: str | Sequence[str] | None = "0004_question_bank"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("agent_id", sa.String(length=32), nullable=True),
    )
    op.execute("UPDATE sessions SET agent_id = 'exp_agent' WHERE agent_id IS NULL")
    op.alter_column("sessions", "agent_id", nullable=False)
    op.create_check_constraint(
        "ck_sessions_agent_id",
        "sessions",
        "agent_id IN ('exp_agent', 'teach_agent')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_sessions_agent_id", "sessions", type_="check")
    op.drop_column("sessions", "agent_id")
