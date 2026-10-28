from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Users


class ChatSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "agent_id IN ('exp_agent', 'teach_agent')",
            name="ck_sessions_agent_id",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(100), default="新会话")

    user: Mapped[Users] = relationship(back_populates="sessions")
