from __future__ import annotations

import base64
from collections.abc import Sequence

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 32


class _FakeModel(FakeMessagesListChatModel):
    def bind_tools(
        self,
        tools: Sequence[object],
        *,
        tool_choice: str | None = None,
        **kwargs: object,
    ) -> _FakeModel:
        return self


def _backend(store: InMemoryStore) -> CompositeBackend:
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/blobs/": StoreBackend(
                namespace=lambda rt: ("test", "blobs"),
                store=store,
            ),
        },
    )


def test_images_are_offloaded_to_blobs() -> None:
    store = InMemoryStore()
    backend = _backend(store)
    agent = create_deep_agent(
        model=_FakeModel(responses=[AIMessage(content="ok")]),
        backend=backend,
        middleware=[
            FilesystemMiddleware(
                backend=backend,
                offload_binary_content=True,
            )
        ],
        checkpointer=InMemorySaver(),
        store=store,
    )
    thread: RunnableConfig = {"configurable": {"thread_id": "t1"}}

    agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=[
                        {"type": "text", "text": "看图"},
                        {
                            "type": "image",
                            "base64": base64.b64encode(PNG).decode(),
                            "mime_type": "image/png",
                        },
                    ]
                )
            ]
        },
        config=thread,
    )

    messages = agent.get_state(thread).values["messages"]
    [human] = [message for message in messages if isinstance(message, HumanMessage)]
    [block] = [
        part
        for part in human.content
        if isinstance(part, dict) and part["type"] == "image"
    ]

    assert block["deepagents_blob"]
    assert "base64" not in block
    assert store.search(("test", "blobs"))
