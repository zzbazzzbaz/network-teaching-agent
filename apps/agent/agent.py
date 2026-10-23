from typing import Any

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from infra.model import get_llm
from prompt import SYSTEM_PROMPT
from tools import make_ask_human


def build_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    return create_deep_agent(
        model=get_llm(),
        system_prompt=SYSTEM_PROMPT,
        tools=[make_ask_human()],
        # backend=
    )
