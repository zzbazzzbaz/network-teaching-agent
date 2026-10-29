from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.file import File


class FileRepository:
    def create(
        self,
        session: Session,
        *,
        file_id: uuid.UUID,
        owner_id: uuid.UUID,
        original_name: str,
        size_bytes: int,
        storage_key: str,
    ) -> File:
        record = File(
            file_id=file_id,
            owner_id=owner_id,
            original_name=original_name,
            size_bytes=size_bytes,
            storage_key=storage_key,
        )
        session.add(record)
        session.flush()
        return record

    def get_owned(
        self,
        session: Session,
        *,
        owner_id: uuid.UUID,
        file_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> File | None:
        conditions = [File.file_id == file_id, File.owner_id == owner_id]
        if not include_deleted:
            conditions.append(File.deleted_at.is_(None))
        return session.scalar(select(File).where(*conditions))

    def get(self, session: Session, *, file_id: uuid.UUID) -> File | None:
        return session.get(File, file_id)

    def mark_deleted(self, session: Session, record: File) -> None:
        if record.deleted_at is None:
            record.deleted_at = datetime.now(UTC)
            session.commit()


file_repository = FileRepository()
