from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSandbox(Base):
    __tablename__ = "user_sandboxes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'paused', 'stopping')",
            name="ck_user_sandboxes_status",
        ),
        Index("ix_user_sandboxes_status_last_active_at", "status", "last_active_at"),
        Index("ix_user_sandboxes_status_hard_destroy_at", "status", "hard_destroy_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    sandbox_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hard_destroy_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
