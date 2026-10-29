from __future__ import annotations

import logging
import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Response, UploadFile

from app.api.dependencies import SessionDep, SettingsDep, UserIdDep
from app.api.schemas.file import FileUploadResponse
from app.core.exceptions import AppError, ValidationError
from app.models.file import File as FileRecord
from app.services import file_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=FileUploadResponse, status_code=201, summary="上传图片")
def upload_file(
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
    file: Annotated[UploadFile | None, File()] = None,
) -> FileUploadResponse:
    if file is None:
        raise ValidationError("缺少文件")

    data = file.file.read(settings.files.max_bytes + 1)
    try:
        record = file_service.upload(
            session,
            owner_id=user_id,
            filename=file.filename,
            content_type=file.content_type,
            data=data,
            root=settings.files.root,
            max_bytes=settings.files.max_bytes,
        )
    except AppError as e:
        logger.info(
            "file_rejected reason=%s mime=%s bytes=%s",
            type(e).__name__,
            file.content_type,
            len(data),
        )
        raise
    return _to_upload_response(record)


@router.get("/{file_id}/raw", summary="读取原图")
def get_raw(
    file_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> Response:
    content, mime, name = file_service.read(
        session,
        owner_id=user_id,
        file_id=file_id,
        thumb=False,
        root=settings.files.root,
    )
    return _image_response(content, mime, name)


@router.get("/{file_id}/thumb", summary="读取缩略图")
def get_thumb(
    file_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> Response:
    content, mime, name = file_service.read(
        session,
        owner_id=user_id,
        file_id=file_id,
        thumb=True,
        root=settings.files.root,
    )
    return _image_response(content, mime, name)


@router.delete("/{file_id}", status_code=204, summary="删除图片")
def delete_file(
    file_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> Response:
    file_service.delete(
        session,
        owner_id=user_id,
        file_id=file_id,
        root=settings.files.root,
    )
    return Response(status_code=204)


def _to_upload_response(record: FileRecord) -> FileUploadResponse:
    return FileUploadResponse(
        file_id=record.file_id,
        name=record.original_name,
        mime=file_service.mime_for_record(record),
        size_bytes=record.size_bytes,
        created_at=record.created_at,
    )


def _image_response(content: bytes, mime: str, name: str) -> Response:
    filename = quote(name, safe="")
    return Response(
        content=content,
        media_type=mime,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{filename}",
            "Cache-Control": "private, max-age=3600",
        },
    )
