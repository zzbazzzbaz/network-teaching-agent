from typing import Any

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.infra.model import get_llm
from agent.prompt.prompt import SYSTEM_PROMPT
from agent.tools.demo1_tool import make_ask_human


def build_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    return create_deep_agent(
        model=get_llm(),
        system_prompt=SYSTEM_PROMPT,
        tools=[make_ask_human()],
        # backend=
    )
