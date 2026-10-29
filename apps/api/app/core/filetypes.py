"""图片格式识别与 MIME/扩展名映射。

图片的 MIME 不落库，统一由 storage_key 的后缀推导；上传时 magic 是唯一
可信来源，客户端 Content-Type 只用于快速拒绝 SVG 等明确类型。
"""

from __future__ import annotations

from pathlib import PurePosixPath

IMAGE_JPEG = "image/jpeg"
IMAGE_PNG = "image/png"
IMAGE_WEBP = "image/webp"

SUPPORTED_IMAGE_MIME_TYPES = frozenset({IMAGE_JPEG, IMAGE_PNG, IMAGE_WEBP})

_MIME_BY_EXTENSION = {
    ".jpg": IMAGE_JPEG,
    ".jpeg": IMAGE_JPEG,
    ".png": IMAGE_PNG,
    ".webp": IMAGE_WEBP,
}

_EXTENSION_BY_MIME = {
    IMAGE_JPEG: "jpg",
    IMAGE_PNG: "png",
    IMAGE_WEBP: "webp",
}


def detect_image_mime(data: bytes) -> str | None:
    """按文件头判断图片类型；不支持的类型返回 None。"""
    if data.startswith(b"\xff\xd8\xff"):
        return IMAGE_JPEG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return IMAGE_PNG
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return IMAGE_WEBP
    return None


def extension_for_mime(mime: str) -> str:
    try:
        return _EXTENSION_BY_MIME[mime]
    except KeyError as e:
        raise ValueError(f"不支持的图片类型：{mime}") from e


def mime_for_storage_key(storage_key: str) -> str:
    suffix = PurePosixPath(storage_key).suffix.lower()
    try:
        return _MIME_BY_EXTENSION[suffix]
    except KeyError as e:
        raise ValueError(f"无法从存储路径推导图片类型：{storage_key}") from e
