import os
from typing import Any

from deepagents import FilesystemPermission
from langgraph.runtime import Runtime

from agent.runtime.paths import AgentName


def memory_namespace(rt: Runtime[Any]) -> tuple[str, ...]:
    user = rt.server_info.user if rt.server_info is not None else None
    if user is not None:
        return "users", user.identity, "memory"

    # langgraph dev 通过该标记运行，允许本地无 auth 的调试记忆。
    if os.getenv("LANGSMITH_LANGGRAPH_API_VARIANT") == "local_dev":
        return "users", "local", "memory"

    raise RuntimeError("未认证用户，无法加载用户记忆")


def memory_permissions(agent: AgentName) -> list[FilesystemPermission]:
    own = "/memory/lab/**" if agent == "exp" else "/memory/teaching/**"

    rules = [
        FilesystemPermission(
            operations=["write"],
            paths=[own],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=["/memory/AGENTS.md", "/memory/profile.md"],
            mode="allow",
        ),
    ]

    if agent == "exp":
        rules.append(
            FilesystemPermission(
                operations=["write"],
                paths=["/root/workspace/**"],
                mode="allow",
            )
        )

    rules.append(
        FilesystemPermission(
            operations=["write"],
            paths=["/**"],
            mode="deny",
        )
    )
    return rules
