import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.pagination import PageRequest, PageResult
from app.models.session import ChatSession


class SessionRepository:
    def list_by_owner(
        self,
        session: Session,
        owner_id: uuid.UUID,
        *,
        page: PageRequest,
        agent_id: str | None = None,
    ) -> PageResult[ChatSession]:
        conditions = [ChatSession.user_id == owner_id]
        if agent_id is not None:
            conditions.append(ChatSession.agent_id == agent_id)
        base = select(ChatSession).where(*conditions)
        total = session.scalar(
            select(func.count()).select_from(base.order_by(None).subquery())
        )
        items = list(
            session.scalars(
                base.order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        return PageResult(
            items=items,
            total=int(total or 0),
            limit=page.limit,
            offset=page.offset,
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

    def create(
        self,
        session: Session,
        *,
        owner_id: uuid.UUID,
        agent_id: str,
        title: str,
    ) -> ChatSession:
        chat_session = ChatSession(user_id=owner_id, agent_id=agent_id, title=title)
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
