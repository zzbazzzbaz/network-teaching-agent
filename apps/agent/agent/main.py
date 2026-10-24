from typing import Any

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.observability import get_langfuse_handler
from agent.infra.ags_backend import AgsBackend
from agent.infra.model import get_llm
from agent.prompt.prompt import SYSTEM_PROMPT
from agent.tools.demo1_tool import make_ask_human


def build_exp_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=SYSTEM_PROMPT,
        tools=[make_ask_human()],
        backend=AgsBackend(),
        name="exp_agent",
    )
    return graph.with_config({"callbacks": [get_langfuse_handler()]})
