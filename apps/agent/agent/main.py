from pathlib import Path
from typing import Any

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.observability import get_langfuse_handler
from agent.infra.ags_backend import AgsBackend
from agent.infra.model import get_llm
from agent.tools.demo1_tool import make_ask_human

RESOURCE_DIR = Path(__file__).resolve().parent / "resources"
SYSTEM_PROMPT_PATH = RESOURCE_DIR / "prompt" / "system.md"


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _build_backend() -> CompositeBackend:
    return CompositeBackend(
        default=AgsBackend(),
        routes={
            "/skills/": FilesystemBackend(root_dir=RESOURCE_DIR / "skills", virtual_mode=True),
            "/materials/": FilesystemBackend(
                root_dir=RESOURCE_DIR / "materials", virtual_mode=True
            ),
        },
    )


def build_exp_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=_load_system_prompt(),
        tools=[make_ask_human()],
        backend=_build_backend(),
        skills=["/skills/"],
        permissions=[
            FilesystemPermission(
                operations=["write"],
                paths=["/skills/**", "/materials/**"],
                mode="deny",
            )
        ],
        name="exp_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})
