from __future__ import annotations

import uuid
from datetime import datetime

from app.api.schemas.base import ApiResponse


class FileMetadataResponse(ApiResponse):
    file_id: uuid.UUID
    name: str
    mime: str
    size_bytes: int


class FileUploadResponse(FileMetadataResponse):
    created_at: datetime
