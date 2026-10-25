import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_sandbox import UserSandbox


class UserSandboxRepository:
    def get(self, session: Session, user_id: uuid.UUID) -> UserSandbox | None:
        return session.get(UserSandbox, user_id)

    def get_for_update(self, session: Session, user_id: uuid.UUID) -> UserSandbox | None:
        return session.scalar(
            select(UserSandbox).where(UserSandbox.user_id == user_id).with_for_update()
        )

    def save(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        sandbox_id: str,
        status: str,
        last_active_at: datetime,
        paused_at: datetime | None,
        expires_at: datetime,
        hard_destroy_at: datetime,
    ) -> UserSandbox:
        record = session.get(UserSandbox, user_id)
        if record is None:
            record = UserSandbox(
                user_id=user_id,
                sandbox_id=sandbox_id,
                status=status,
                last_active_at=last_active_at,
                paused_at=paused_at,
                expires_at=expires_at,
                hard_destroy_at=hard_destroy_at,
            )
            session.add(record)
        else:
            record.sandbox_id = sandbox_id
            record.status = status
            record.last_active_at = last_active_at
            record.paused_at = paused_at
            record.expires_at = expires_at
            record.hard_destroy_at = hard_destroy_at
        session.flush()
        return record

    def delete(self, session: Session, record: UserSandbox) -> None:
        session.delete(record)
        session.flush()


user_sandbox_repository = UserSandboxRepository()
