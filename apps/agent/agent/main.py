from typing import Any

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemMiddleware, FsToolName
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.observability import get_langfuse_handler
from agent.infra.model import get_llm
from agent.runtime.backends import build_exp_backend, build_teaching_backend
from agent.runtime.memory import memory_permissions
from agent.runtime.paths import memory_paths, skill_paths
from agent.runtime.prompts import load_prompt
from agent.tools.ask_student import make_ask_student

TEACH_FS_TOOLS: list[FsToolName] = ["ls", "read_file", "write_file", "edit_file", "glob", "grep"]


def build_exp_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=load_prompt("base", "lab"),
        tools=[make_ask_student()],
        backend=build_exp_backend(),
        skills=skill_paths("exp"),
        memory=memory_paths("exp"),
        permissions=memory_permissions("exp"),
        name="exp_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})


def build_teach_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    backend = build_teaching_backend()
    permissions = memory_permissions("teach")

    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=load_prompt("base", "teaching"),
        tools=[make_ask_student()],
        backend=backend,
        middleware=[
            FilesystemMiddleware(
                backend=backend,
                tools=TEACH_FS_TOOLS,
                _permissions=permissions,
            )
        ],
        skills=skill_paths("teach"),
        memory=memory_paths("teach"),
        permissions=permissions,
        name="teach_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})
