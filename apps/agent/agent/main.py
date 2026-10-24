from typing import Any

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.observability import TRACE_NAME, TRACE_TAGS, get_langfuse_handler
from agent.infra.model import get_llm
from agent.prompt.prompt import SYSTEM_PROMPT
from agent.tools.demo1_tool import make_ask_human


def build_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    graph = create_deep_agent(
        model=get_llm(),
        system_prompt=SYSTEM_PROMPT,
        tools=[make_ask_human()],
        # backend=
    )
    # LangGraph Server 不会替调用方注入回调，绑在默认 config 上才能覆盖每次 run。
    return graph.with_config(
        {
            "callbacks": [get_langfuse_handler()],
            "run_name": TRACE_NAME,
            "metadata": {"langfuse_tags": TRACE_TAGS},
        }
    )
