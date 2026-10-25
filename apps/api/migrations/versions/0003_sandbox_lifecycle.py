"""add sandbox lifecycle fields

Revision ID: 0003_sandbox_lifecycle
Revises: 0002_user_sandboxes
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_sandbox_lifecycle"
down_revision: str | Sequence[str] | None = "0002_user_sandboxes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_sandboxes",
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_sandboxes",
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_sandboxes",
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_sandboxes",
        sa.Column("hard_destroy_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE user_sandboxes
        SET last_active_at = updated_at,
            hard_destroy_at = created_at + interval '7 days'
        """
    )

    op.alter_column("user_sandboxes", "last_active_at", nullable=False)
    op.alter_column("user_sandboxes", "hard_destroy_at", nullable=False)
    op.alter_column("user_sandboxes", "status", server_default=None)

    op.create_check_constraint(
        "ck_user_sandboxes_status",
        "user_sandboxes",
        "status IN ('running', 'paused', 'stopping')",
    )
    op.create_index(
        "ix_user_sandboxes_status_last_active_at",
        "user_sandboxes",
        ["status", "last_active_at"],
    )
    op.create_index(
        "ix_user_sandboxes_status_hard_destroy_at",
        "user_sandboxes",
        ["status", "hard_destroy_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_sandboxes_status_hard_destroy_at",
        table_name="user_sandboxes",
    )
    op.drop_index(
        "ix_user_sandboxes_status_last_active_at",
        table_name="user_sandboxes",
    )
    op.drop_constraint(
        "ck_user_sandboxes_status",
        "user_sandboxes",
        type_="check",
    )
    op.drop_column("user_sandboxes", "hard_destroy_at")
    op.drop_column("user_sandboxes", "paused_at")
    op.drop_column("user_sandboxes", "last_active_at")
    op.drop_column("user_sandboxes", "status")
