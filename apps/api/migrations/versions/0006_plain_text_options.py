"""strip option letter prefixes

Revision ID: 0006_plain_text_options
Revises: 0005_session_agent
Create Date: 2026-10-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_plain_text_options"
down_revision: str | Sequence[str] | None = "0005_session_agent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE questions
        SET options = (
            SELECT jsonb_agg(
                regexp_replace(value, '^[A-F][.、)）][[:space:]]*', '')
                ORDER BY ordinality
            )
            FROM jsonb_array_elements_text(options) WITH ORDINALITY
                AS item(value, ordinality)
        )
        WHERE options IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE questions
        SET options = (
            SELECT jsonb_agg(
                chr((65 + ordinality - 1)::int) || '. ' || value
                ORDER BY ordinality
            )
            FROM jsonb_array_elements_text(options) WITH ORDINALITY
                AS item(value, ordinality)
        )
        WHERE question_type = 'single_choice' AND options IS NOT NULL
        """
    )
