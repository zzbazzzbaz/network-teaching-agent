from pydantic import BaseModel, Field

from app.api.schemas.base import ApiResponse


class PageQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class Page[T](ApiResponse):
    items: list[T]
    total: int
    limit: int
    offset: int
