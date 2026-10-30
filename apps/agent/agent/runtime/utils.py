import os
from typing import Any

from langgraph.runtime import Runtime

from agent.core.constants import PROMPT_DIR


def load_prompt(*parts: str) -> str:
    return "\n\n".join(
        (PROMPT_DIR / f"{part}.md").read_text(encoding="utf-8").strip() for part in parts
    )


def user_namespace(rt: Runtime[Any], kind: str) -> tuple[str, ...]:
    user = rt.server_info.user if rt.server_info is not None else None
    if user is not None:
        return "users", user.identity, kind

    # langgraph dev 通过该标记运行，允许本地无 auth 的调试数据。
    if os.getenv("LANGSMITH_LANGGRAPH_API_VARIANT") == "local_dev":
        return "users", "local", kind

    raise RuntimeError("未认证用户，无法读取用户文件")


def memory_namespace(rt: Runtime[Any]) -> tuple[str, ...]:
    return user_namespace(rt, "memory")


def blob_namespace(rt: Runtime[Any]) -> tuple[str, ...]:
    return user_namespace(rt, "blobs")
