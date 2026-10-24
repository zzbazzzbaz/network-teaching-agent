import uuid

from fastapi import APIRouter, Response

from app.api.dependencies import SessionDep, UserIdDep
from app.api.schemas.session import CreateSessionBody, SessionResponse, UpdateSessionBody
from app.models.session import ChatSession
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
def list_sessions(session: SessionDep, user_id: UserIdDep) -> list[ChatSession]:
    return session_service.list_sessions(owner_id=user_id, session=session)


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(
    body: CreateSessionBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> ChatSession:
    return session_service.create_session(owner_id=user_id, title=body.title, session=session)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> ChatSession:
    return session_service.get_owned_session(
        owner_id=user_id,
        session_id=session_id,
        session=session,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
def rename_session(
    session_id: uuid.UUID,
    body: UpdateSessionBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> ChatSession:
    return session_service.rename_session(
        owner_id=user_id,
        session_id=session_id,
        title=body.title,
        session=session,
    )


@router.post("/{session_id}/touch", status_code=204)
def touch_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> Response:
    session_service.touch_session(owner_id=user_id, session_id=session_id, session=session)
    return Response(status_code=204)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> Response:
    session_service.delete_session(owner_id=user_id, session_id=session_id, session=session)
    return Response(status_code=204)
