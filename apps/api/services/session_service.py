import uuid

from sqlalchemy.orm import Session

from core.constants import DEFAULT_SESSION_TITLE, MAX_SESSION_TITLE_LENGTH
from core.exceptions import NotFoundError, ValidationError
from models.session import ChatSession
from repositories.session_repository import session_repository


def _normalize_title(title: str) -> str:
    resolved = title.strip() or DEFAULT_SESSION_TITLE
    if len(resolved) > MAX_SESSION_TITLE_LENGTH:
        raise ValidationError(f"会话名称不能超过 {MAX_SESSION_TITLE_LENGTH} 个字符")
    return resolved


def list_sessions(*, owner_id: uuid.UUID, session: Session) -> list[ChatSession]:
    return session_repository.list_by_owner(session, owner_id)


def get_owned_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    session: Session,
) -> ChatSession:
    chat_session = session_repository.get_owned(
        session,
        session_id=session_id,
        owner_id=owner_id,
    )
    if chat_session is None:
        raise NotFoundError("会话不存在")
    return chat_session


def create_session(*, owner_id: uuid.UUID, title: str, session: Session) -> ChatSession:
    return session_repository.create(
        session,
        owner_id=owner_id,
        title=_normalize_title(title),
    )


def rename_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    title: str,
    session: Session,
) -> ChatSession:
    chat_session = get_owned_session(owner_id=owner_id, session_id=session_id, session=session)
    return session_repository.rename(session, chat_session, title=_normalize_title(title))


def touch_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    session: Session,
) -> None:
    chat_session = get_owned_session(owner_id=owner_id, session_id=session_id, session=session)
    session_repository.touch(session, chat_session)


def delete_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    session: Session,
) -> None:
    chat_session = get_owned_session(owner_id=owner_id, session_id=session_id, session=session)
    session_repository.delete(session, chat_session)
