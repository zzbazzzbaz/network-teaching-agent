import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user_sandbox import UserSandbox


class UserSandboxRepository:
    def get(self, session: Session, user_id: uuid.UUID) -> UserSandbox | None:
        return session.get(UserSandbox, user_id)

    def save(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        sandbox_id: str,
        expires_at: datetime,
    ) -> UserSandbox:
        record = session.get(UserSandbox, user_id)
        if record is None:
            record = UserSandbox(
                user_id=user_id,
                sandbox_id=sandbox_id,
                expires_at=expires_at,
            )
            session.add(record)
        else:
            record.sandbox_id = sandbox_id
            record.expires_at = expires_at
        session.flush()
        return record

    def delete(self, session: Session, record: UserSandbox) -> None:
        session.delete(record)
        session.flush()


user_sandbox_repository = UserSandboxRepository()
