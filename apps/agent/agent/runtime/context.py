from dataclasses import dataclass

from langgraph.prebuilt import ToolRuntime


@dataclass(frozen=True)
class ToolContext:
    user_id: str
    thread_id: str
    tool_call_id: str


def tool_context(runtime: ToolRuntime) -> ToolContext:
    """读取 LangGraph 注入的运行时身份；缺失时直接失败，避免静默降级。"""
    configurable = runtime.config["configurable"]
    tool_call_id = runtime.tool_call_id
    if tool_call_id is None:
        raise RuntimeError("缺少 tool_call_id")
    return ToolContext(
        user_id=configurable["langgraph_auth_user_id"],
        thread_id=configurable["thread_id"],
        tool_call_id=tool_call_id,
    )
