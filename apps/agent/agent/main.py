from typing import Any

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import (
    CompositeBackend,
    FilesystemBackend,
    StateBackend,
    StoreBackend,
)
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents.middleware import AgentMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.constants import SKILLS_DIR
from agent.core.observability import get_langfuse_handler
from agent.infra.ags_backend import AgsBackend
from agent.infra.model import get_llm
from agent.runtime.session_title import SessionTitleMiddleware
from agent.runtime.utils import blob_namespace, load_prompt, memory_namespace
from agent.tools.ask_student import make_ask_student
from agent.tools.question_bank import make_question_bank_tools


def build_exp_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    backend = CompositeBackend(
        default=AgsBackend(),
        routes={
            "/skills/": FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True),
            "/memory/": StoreBackend(namespace=memory_namespace),
            "/blobs/": StoreBackend(namespace=blob_namespace),
        },
    )
    permissions = [
        FilesystemPermission(
            operations=["write"],
            paths=["/memory/lab/**"],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=["/memory/AGENTS.md", "/memory/profile.md"],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=["/memory/**"],
            mode="deny",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=["/skills/**"],
            mode="deny",
        ),
    ]
    # 自定义 FilesystemMiddleware 会按名字替换 deepagents 的默认实例，权限要重新挂。
    middleware: list[AgentMiddleware[Any, None, Any]] = [
        FilesystemMiddleware(
            backend=backend,
            offload_binary_content=True,
            _permissions=permissions,
        ),
        SessionTitleMiddleware(),
    ]
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=load_prompt("base", "lab"),
        backend=backend,
        permissions=permissions,
        skills=["/skills/common/", "/skills/lab/"],
        memory=["/memory/AGENTS.md", "/memory/lab/AGENTS.md"],
        middleware=middleware,
        name="exp_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})


def build_teach_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/": FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True),
            "/memory/": StoreBackend(namespace=memory_namespace),
            "/blobs/": StoreBackend(namespace=blob_namespace),
        },
    )
    permissions = [
        FilesystemPermission(
            operations=["write"],
            paths=["/memory/teaching/**"],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=["/memory/AGENTS.md", "/memory/profile.md"],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=["/**"],
            mode="deny",
        ),
    ]
    # 自定义 FilesystemMiddleware 会按名字替换 deepagents 的默认实例，权限要重新挂。
    middleware: list[AgentMiddleware[Any, None, Any]] = [
        FilesystemMiddleware(
            backend=backend,
            offload_binary_content=True,
            _permissions=permissions,
        ),
        SessionTitleMiddleware(),
    ]
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=load_prompt("base", "teaching"),
        tools=[
            make_ask_student(),
            *make_question_bank_tools(),
        ],
        backend=backend,
        permissions=permissions,
        skills=["/skills/common/", "/skills/teaching/"],
        memory=["/memory/AGENTS.md", "/memory/teaching/AGENTS.md"],
        middleware=middleware,
        name="teach_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})
