from typing import Any

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.observability import get_langfuse_handler
from agent.infra.model import get_llm
from agent.runtime.backends import build_exp_backend, build_teaching_backend
from agent.runtime.memory import exp_memory_permissions, teach_memory_permissions
from agent.runtime.paths import memory_paths, skill_paths
from agent.runtime.prompts import load_prompt
from agent.tools.ask_student import make_ask_student
from agent.tools.question_bank import make_question_bank_tools


def build_exp_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=load_prompt("base", "lab"),
        tools=[],
        backend=build_exp_backend(),
        skills=skill_paths("exp"),
        memory=memory_paths("exp"),
        permissions=exp_memory_permissions(),
        name="exp_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})


def build_teach_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=load_prompt("base", "teaching"),
        tools=[
            make_ask_student(),
            *make_question_bank_tools(),
        ],
        backend=build_teaching_backend(),
        skills=skill_paths("teach"),
        memory=memory_paths("teach"),
        permissions=teach_memory_permissions(),
        name="teach_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})
