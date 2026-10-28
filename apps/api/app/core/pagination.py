from dataclasses import dataclass


@dataclass(frozen=True)
class PageRequest:
    limit: int
    offset: int


@dataclass(frozen=True)
class PageResult[T]:
    items: list[T]
    total: int
    limit: int
    offset: int
