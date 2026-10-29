from __future__ import annotations

import uuid

from app.gateway.agent import AgentGateway, StoreItem


class FakeAgentGateway(AgentGateway):
    """测试替身：不访问网络，记录调用，可注入失败。"""

    def __init__(self) -> None:
        self.items: list[StoreItem] = []
        self.item: StoreItem | None = None
        self.fail: Exception | None = None
        self.search_calls: list[uuid.UUID] = []
        self.get_calls: list[tuple[uuid.UUID, str]] = []
        self.thread_calls: list[tuple[str, uuid.UUID, str]] = []

    def search_memory(self, *, user_id: uuid.UUID) -> list[StoreItem]:
        self.search_calls.append(user_id)
        if self.fail is not None:
            raise self.fail
        return self.items

    def get_memory(self, *, user_id: uuid.UUID, key: str) -> StoreItem | None:
        self.get_calls.append((user_id, key))
        if self.fail is not None:
            raise self.fail
        return self.item

    def ensure_thread(self, *, user_id: uuid.UUID, thread_id: str) -> None:
        self.thread_calls.append(("ensure", user_id, thread_id))
        if self.fail is not None:
            raise self.fail

    def delete_thread(self, *, user_id: uuid.UUID, thread_id: str) -> None:
        self.thread_calls.append(("delete", user_id, thread_id))
        if self.fail is not None:
            raise self.fail
