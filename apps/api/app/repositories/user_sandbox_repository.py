import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.models.user_sandbox import SandboxStatus, UserSandbox


class UserSandboxRepository:
    def get(self, session: Session, user_id: uuid.UUID) -> UserSandbox | None:
        return session.get(UserSandbox, user_id)

    def get_for_update(self, session: Session, user_id: uuid.UUID) -> UserSandbox | None:
        return session.scalar(
            select(UserSandbox).where(UserSandbox.user_id == user_id).with_for_update()
        )

    def create(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        sandbox_id: str,
        status: SandboxStatus,
        last_active_at: datetime,
        paused_at: datetime | None,
        expires_at: datetime,
        hard_destroy_at: datetime,
    ) -> UserSandbox:
        record = UserSandbox(
            user_id=user_id,
            sandbox_id=sandbox_id,
            status=status.value,
            last_active_at=last_active_at,
            paused_at=paused_at,
            expires_at=expires_at,
            hard_destroy_at=hard_destroy_at,
        )
        session.add(record)
        session.flush()
        return record

    def delete(self, session: Session, record: UserSandbox) -> None:
        session.delete(record)
        session.flush()

    def claim_idle_running(
        self,
        session: Session,
        *,
        idle_before: datetime,
        now: datetime,
        exclude: Collection[uuid.UUID],
    ) -> UserSandbox | None:
        return self._claim_one(
            session,
            UserSandbox.status == SandboxStatus.RUNNING.value,
            UserSandbox.last_active_at <= idle_before,
            UserSandbox.hard_destroy_at > now,
            order_by=UserSandbox.last_active_at,
            exclude=exclude,
        )

    def claim_paused_expired(
        self,
        session: Session,
        *,
        paused_before: datetime,
        exclude: Collection[uuid.UUID],
    ) -> UserSandbox | None:
        return self._claim_one(
            session,
            UserSandbox.status == SandboxStatus.PAUSED.value,
            UserSandbox.paused_at.is_not(None),
            UserSandbox.paused_at <= paused_before,
            order_by=UserSandbox.paused_at,
            exclude=exclude,
        )

    def claim_over_lifetime(
        self,
        session: Session,
        *,
        now: datetime,
        exclude: Collection[uuid.UUID],
    ) -> UserSandbox | None:
        return self._claim_one(
            session,
            UserSandbox.status.in_(
                (SandboxStatus.RUNNING.value, SandboxStatus.PAUSED.value)
            ),
            UserSandbox.hard_destroy_at <= now,
            order_by=UserSandbox.hard_destroy_at,
            exclude=exclude,
        )

    def claim_stopping(
        self,
        session: Session,
        *,
        exclude: Collection[uuid.UUID],
    ) -> UserSandbox | None:
        return self._claim_one(
            session,
            UserSandbox.status == SandboxStatus.STOPPING.value,
            order_by=UserSandbox.updated_at,
            exclude=exclude,
        )

    def _claim_one(
        self,
        session: Session,
        *conditions: ColumnElement[bool],
        order_by: InstrumentedAttribute[Any],
        exclude: Collection[uuid.UUID],
    ) -> UserSandbox | None:
        query = select(UserSandbox).where(*conditions)
        if exclude:
            query = query.where(UserSandbox.user_id.not_in(exclude))
        return session.scalar(
            query.order_by(order_by).with_for_update(skip_locked=True).limit(1)
        )


user_sandbox_repository = UserSandboxRepository()
