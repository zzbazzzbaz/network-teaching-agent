import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.user import Users


class Session(Base):
    __tablename__ = "session"

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"), on_delete="CASCADE")
    title: Mapped[str] = mapped_column(String(32))

    user: Mapped[Users] = relationship(back_populates="session")
