from __future__ import annotations

import uuid

from fastapi import APIRouter, Response

from app.api.dependencies import InternalUserDep, SessionDep, SettingsDep
from app.api.schemas.file import FileMetadataResponse
from app.models.file import File as FileRecord
from app.services import file_service

router = APIRouter(tags=["internal-files"], include_in_schema=False)


@router.get("/{file_id}", response_model=FileMetadataResponse)
def get_file_metadata(
    file_id: uuid.UUID,
    session: SessionDep,
    user_id: InternalUserDep,
) -> FileMetadataResponse:
    record = file_service.get_owned(
        session,
        owner_id=user_id,
        file_id=file_id,
    )
    return _to_metadata(record)


@router.get("/{file_id}/raw")
def get_file_raw(
    file_id: uuid.UUID,
    session: SessionDep,
    user_id: InternalUserDep,
    settings: SettingsDep,
) -> Response:
    content, mime, _ = file_service.read(
        session,
        owner_id=user_id,
        file_id=file_id,
        thumb=False,
        root=settings.files.root,
    )
    return Response(
        content=content,
        media_type=mime,
        headers={"Cache-Control": "private, max-age=3600"},
    )


def _to_metadata(record: FileRecord) -> FileMetadataResponse:
    return FileMetadataResponse(
        file_id=record.file_id,
        name=record.original_name,
        mime=file_service.mime_for_record(record),
        size_bytes=record.size_bytes,
    )
