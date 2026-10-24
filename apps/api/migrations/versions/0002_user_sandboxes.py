"""add user sandboxes

Revision ID: 0002_user_sandboxes
Revises: 0001_initial
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_sandboxes"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_sandboxes",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("sandbox_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "ix_user_sandboxes_sandbox_id",
        "user_sandboxes",
        ["sandbox_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_user_sandboxes_sandbox_id", table_name="user_sandboxes")
    op.drop_table("user_sandboxes")
