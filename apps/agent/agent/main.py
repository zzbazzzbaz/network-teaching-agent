import os
from pathlib import Path
from typing import Any

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime

from agent.core.observability import get_langfuse_handler
from agent.infra.ags_backend import AgsBackend
from agent.infra.model import get_llm
from agent.tools.demo1_tool import make_ask_human

RESOURCE_DIR = Path(__file__).resolve().parent / "resources"
SYSTEM_PROMPT_PATH = RESOURCE_DIR / "prompt" / "system.md"


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _memory_namespace(rt: Runtime[Any]) -> tuple[str, ...]:
    user = rt.server_info.user if rt.server_info is not None else None
    if user is not None:
        return ("users", user.identity, "memory")

    # langgraph dev 通过该标记运行，允许本地无 auth 的调试记忆。
    if os.getenv("LANGSMITH_LANGGRAPH_API_VARIANT") == "local_dev":
        return ("users", "local", "memory")

    raise RuntimeError("未认证用户，无法加载用户记忆")


def _build_backend() -> CompositeBackend:
    return CompositeBackend(
        default=AgsBackend(),
        routes={
            "/skills/": FilesystemBackend(root_dir=RESOURCE_DIR / "skills", virtual_mode=True),
            "/materials/": FilesystemBackend(
                root_dir=RESOURCE_DIR / "materials", virtual_mode=True
            ),
            "/memory/": StoreBackend(namespace=_memory_namespace),
        },
    )


def build_exp_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=_load_system_prompt(),
        tools=[make_ask_human()],
        backend=_build_backend(),
        skills=["/skills/"],
        memory=["/memory/AGENTS.md"],
        permissions=[
            FilesystemPermission(
                operations=["write"],
                paths=["/memory/**"],
                mode="allow",
            ),
            FilesystemPermission(
                operations=["write"],
                paths=["/skills/**", "/materials/**"],
                mode="deny",
            ),
        ],
        name="exp_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})
