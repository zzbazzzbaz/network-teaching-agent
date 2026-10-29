import uuid

from sqlalchemy.orm import Session

from app.core.constants import (
    DEFAULT_SESSION_TITLE,
    MAX_AUTO_TITLE_LENGTH,
    MAX_SESSION_TITLE_LENGTH,
    SESSION_TITLE_SOURCE_DEFAULT,
    SESSION_TITLE_SOURCE_USER,
)
from app.core.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    UnprocessableError,
    ValidationError,
)
from app.core.pagination import PageRequest, PageResult
from app.gateway.agent import AgentGateway
from app.gateway.http_client import UpstreamError
from app.models.session import ChatSession
from app.repositories.session_repository import session_repository


def _normalize_title(title: str) -> str:
    resolved = title.strip() or DEFAULT_SESSION_TITLE
    if len(resolved) > MAX_SESSION_TITLE_LENGTH:
        raise ValidationError(f"会话名称不能超过 {MAX_SESSION_TITLE_LENGTH} 个字符")
    return resolved


def _normalize_auto_title(title: str) -> str:
    resolved = " ".join(title.split())
    if not resolved:
        raise UnprocessableError("会话标题不能为空")
    return resolved[:MAX_AUTO_TITLE_LENGTH]


def list_sessions(
    *,
    owner_id: uuid.UUID,
    session: Session,
    page: PageRequest,
    agent_id: str | None = None,
) -> PageResult[ChatSession]:
    return session_repository.list_by_owner(
        session,
        owner_id,
        page=page,
        agent_id=agent_id,
    )


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


def create_session(
    *,
    owner_id: uuid.UUID,
    agent_id: str,
    title: str,
    session: Session,
    agent: AgentGateway,
) -> ChatSession:
    chat_session = session_repository.create(
        session,
        owner_id=owner_id,
        agent_id=agent_id,
        title=_normalize_title(title),
        title_source=(
            SESSION_TITLE_SOURCE_USER if title.strip() else SESSION_TITLE_SOURCE_DEFAULT
        ),
    )
    try:
        agent.ensure_thread(user_id=owner_id, thread_id=str(chat_session.session_id))
    except UpstreamError as e:
        session_repository.delete(session, chat_session)
        raise ServiceUnavailableError("会话服务暂不可用") from e
    return chat_session


def rename_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    title: str,
    session: Session,
) -> ChatSession:
    chat_session = get_owned_session(owner_id=owner_id, session_id=session_id, session=session)
    return session_repository.rename(session, chat_session, title=_normalize_title(title))


def auto_title_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    title: str,
    session: Session,
) -> tuple[ChatSession, bool]:
    chat_session, updated = session_repository.auto_title(
        session,
        session_id=session_id,
        owner_id=owner_id,
        title=_normalize_auto_title(title),
    )
    if chat_session is None:
        raise NotFoundError("会话不存在")
    return chat_session, updated


def touch_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    session: Session,
) -> None:
    chat_session = get_owned_session(owner_id=owner_id, session_id=session_id, session=session)
    session_repository.touch(session, chat_session)


def ensure_thread(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    session: Session,
    agent: AgentGateway,
) -> None:
    get_owned_session(owner_id=owner_id, session_id=session_id, session=session)
    try:
        agent.ensure_thread(user_id=owner_id, thread_id=str(session_id))
    except UpstreamError as e:
        raise ServiceUnavailableError("会话服务暂不可用") from e


def delete_session(
    *,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    session: Session,
    agent: AgentGateway,
) -> None:
    chat_session = get_owned_session(owner_id=owner_id, session_id=session_id, session=session)
    try:
        agent.delete_thread(user_id=owner_id, thread_id=str(session_id))
    except UpstreamError as e:
        raise ServiceUnavailableError("会话服务暂不可用") from e
    session_repository.delete(session, chat_session)
