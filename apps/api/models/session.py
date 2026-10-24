from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from models.user import Users


class ChatSession(Base):
    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(100), default="新会话")

    user: Mapped[Users] = relationship(back_populates="sessions")
