from __future__ import annotations

import io
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from app.core.filetypes import (
    detect_image_mime,
    extension_for_mime,
    mime_for_storage_key,
)
from app.models.file import File
from app.repositories.file_repository import file_repository

logger = logging.getLogger(__name__)

MAX_IMAGE_EDGE = 8192
MAX_IMAGE_PIXELS = 40_000_000
MAX_LONG_EDGE = 2048
THUMB_LONG_EDGE = 320
THUMB_MIME = "image/webp"
MAX_ORIGINAL_NAME_LENGTH = 255


@dataclass(frozen=True)
class NormalizedImage:
    mime: str
    data: bytes
    thumbnail: bytes


def _normalize_name(filename: str | None) -> str:
    name = Path(filename or "image").name.replace("\x00", "").strip()
    return name[:MAX_ORIGINAL_NAME_LENGTH] or "image"


def _to_rgb(image: Image.Image) -> Image.Image:
    """统一成 RGB；带透明通道的图片铺白底，避免保存时出现黑底。"""
    has_alpha = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    if not has_alpha:
        return image.convert("RGB")

    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def _encode(image: Image.Image, extension: str, *, quality: int) -> bytes:
    output = io.BytesIO()
    if extension == "jpg":
        image.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )
    elif extension == "png":
        image.save(output, format="PNG", optimize=True)
    else:
        image.save(output, format="WEBP", quality=quality, method=4)
    return output.getvalue()


def normalize_image(data: bytes, mime: str) -> NormalizedImage:
    extension = extension_for_mime(mime)
    try:
        with Image.open(io.BytesIO(data)) as opened:
            # 先看 header 再解码，避免为超限图片分配完整像素内存。
            width, height = opened.size
            if (
                width <= 0
                or height <= 0
                or width > MAX_IMAGE_EDGE
                or height > MAX_IMAGE_EDGE
                or width * height > MAX_IMAGE_PIXELS
            ):
                raise UnprocessableError("图片尺寸超出限制")

            opened.load()
            image = ImageOps.exif_transpose(opened)
            if max(width, height) > MAX_LONG_EDGE:
                image.thumbnail(
                    (MAX_LONG_EDGE, MAX_LONG_EDGE),
                    Image.Resampling.LANCZOS,
                )

            image = _to_rgb(image)
            normalized = _encode(image, extension, quality=90)

            thumbnail_image = image.copy()
            thumbnail_image.thumbnail(
                (THUMB_LONG_EDGE, THUMB_LONG_EDGE),
                Image.Resampling.LANCZOS,
            )
            thumbnail = _encode(thumbnail_image, "webp", quality=80)
    except UnprocessableError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as e:
        raise UnprocessableError("图片无法解析或已损坏") from e
    except Exception as e:
        raise UnprocessableError("图片无法解析或已损坏") from e

    return NormalizedImage(mime=mime, data=normalized, thumbnail=thumbnail)


def _thumb_storage_key(storage_key: str) -> str:
    directory, _, _ = storage_key.rpartition("/")
    if not directory:
        raise ValueError(f"非法 storage_key：{storage_key}")
    return f"{directory}/thumb.webp"


def _absolute_path(root: str, storage_key: str) -> Path:
    root_path = Path(root).resolve()
    path = (root_path / storage_key).resolve()
    if not path.is_relative_to(root_path):
        raise ValueError(f"非法存储路径：{storage_key}")
    return path


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def upload(
    session: Session,
    *,
    owner_id: uuid.UUID,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    root: str,
    max_bytes: int,
) -> File:
    started_at = time.perf_counter()
    if not data:
        raise ValidationError("缺少文件内容")
    if len(data) > max_bytes:
        raise PayloadTooLargeError("图片不能超过 10MB")
    if content_type and "svg" in content_type.lower():
        raise UnsupportedMediaTypeError("不支持 SVG 图片")

    mime = detect_image_mime(data)
    if mime is None:
        raise UnsupportedMediaTypeError("仅支持 JPEG、PNG、WebP 图片")

    normalized = normalize_image(data, mime)
    if len(normalized.data) > max_bytes:
        raise PayloadTooLargeError("图片处理后超过 10MB")

    file_id = uuid.uuid4()
    extension = extension_for_mime(normalized.mime)
    storage_key = f"{owner_id}/{file_id}/original.{extension}"
    original_path = _absolute_path(root, storage_key)
    directory = original_path.parent

    committed = False
    try:
        _write_atomic(original_path, normalized.data)
        _write_atomic(directory / "thumb.webp", normalized.thumbnail)
        record = file_repository.create(
            session,
            file_id=file_id,
            owner_id=owner_id,
            original_name=_normalize_name(filename),
            size_bytes=len(normalized.data),
            storage_key=storage_key,
        )
        session.commit()
        committed = True
        session.refresh(record)
    except Exception:
        session.rollback()
        if not committed:
            shutil.rmtree(directory, ignore_errors=True)
        raise

    logger.info(
        "file_uploaded file_id=%s owner_id=%s mime=%s bytes=%s ms=%.1f",
        record.file_id,
        owner_id,
        normalized.mime,
        record.size_bytes,
        (time.perf_counter() - started_at) * 1000,
    )
    return record


def mime_for_record(record: File) -> str:
    return mime_for_storage_key(record.storage_key)


def get_owned(
    session: Session,
    *,
    owner_id: uuid.UUID,
    file_id: uuid.UUID,
) -> File:
    record = file_repository.get_owned(
        session,
        owner_id=owner_id,
        file_id=file_id,
    )
    if record is None:
        raise NotFoundError("图片不存在")
    return record


def read(
    session: Session,
    *,
    owner_id: uuid.UUID,
    file_id: uuid.UUID,
    thumb: bool,
    root: str,
) -> tuple[bytes, str, str]:
    record = get_owned(session, owner_id=owner_id, file_id=file_id)
    try:
        storage_key = _thumb_storage_key(record.storage_key) if thumb else record.storage_key
        path = _absolute_path(root, storage_key)
    except ValueError as e:
        raise NotFoundError("图片不存在") from e
    try:
        content = path.read_bytes()
    except (FileNotFoundError, OSError) as e:
        raise NotFoundError("图片不存在") from e

    if thumb:
        mime = THUMB_MIME
    else:
        try:
            mime = mime_for_storage_key(record.storage_key)
        except ValueError as e:
            raise NotFoundError("图片不存在") from e
    return content, mime, record.original_name


def delete(
    session: Session,
    *,
    owner_id: uuid.UUID,
    file_id: uuid.UUID,
    root: str,
) -> None:
    record = file_repository.get(session, file_id=file_id)
    if record is None:
        return
    if record.owner_id != owner_id:
        raise NotFoundError("图片不存在")
    if record.deleted_at is not None:
        return

    file_repository.mark_deleted(session, record)
    try:
        directory = _absolute_path(root, _thumb_storage_key(record.storage_key)).parent
    except ValueError:
        logger.warning("file_delete_path_invalid file_id=%s", record.file_id)
        return
    shutil.rmtree(directory, ignore_errors=True)
