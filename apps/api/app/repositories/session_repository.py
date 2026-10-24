import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import ChatSession


class SessionRepository:
    def list_by_owner(self, session: Session, owner_id: uuid.UUID) -> list[ChatSession]:
        return list(
            session.scalars(
                select(ChatSession)
                .where(ChatSession.user_id == owner_id)
                .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
            )
        )

    def get_owned(
        self,
        session: Session,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> ChatSession | None:
        return session.scalar(
            select(ChatSession).where(
                ChatSession.session_id == session_id,
                ChatSession.user_id == owner_id,
            )
        )

    def create(self, session: Session, *, owner_id: uuid.UUID, title: str) -> ChatSession:
        chat_session = ChatSession(user_id=owner_id, title=title)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return chat_session

    def rename(self, session: Session, chat_session: ChatSession, *, title: str) -> ChatSession:
        chat_session.title = title
        session.commit()
        session.refresh(chat_session)
        return chat_session

    def touch(self, session: Session, chat_session: ChatSession) -> None:
        chat_session.updated_at = datetime.now(UTC)
        session.commit()

    def delete(self, session: Session, chat_session: ChatSession) -> None:
        session.delete(chat_session)
        session.commit()


session_repository = SessionRepository()
