"""Langfuse 可观测性：初始化客户端并把 LangChain 回调挂到图默认配置上。

LangGraph Server 由服务端统一发起 run，调用方无法逐请求注入 callback，
因此把 CallbackHandler 绑定到 graph 的默认 config；一次 run 自动形成一条 trace，
LLM / tool / chain observation 由 Langfuse 回调自动补全。
"""

from functools import lru_cache

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from agent.core.config import get_settings


@lru_cache
def get_langfuse() -> Langfuse:
    settings = get_settings()
    return Langfuse(
        public_key=settings.langfuse.public_key,
        secret_key=settings.langfuse.secret_key,
        base_url=settings.langfuse.base_url,
    )


@lru_cache
def get_langfuse_handler() -> CallbackHandler:
    """进程内复用一个 handler；并发 run 的 trace 上下文按 run_id 隔离。"""
    get_langfuse()
    return CallbackHandler()
