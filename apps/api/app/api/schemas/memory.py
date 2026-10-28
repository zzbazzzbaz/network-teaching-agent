from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.base import ApiResponse


class MemoryEntry(ApiResponse):
    path: str
    name: str
    kind: Literal["file", "directory"]
    size: int
    modified_at: datetime | None


class MemoryTreeResponse(ApiResponse):
    entries: list[MemoryEntry]


class MemoryFileResponse(ApiResponse):
    path: str
    name: str
    size: int
    modified_at: datetime | None
    content: str


class MemoryFileQuery(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
