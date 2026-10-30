from functools import lru_cache
from uuid import uuid4

from langchain.chat_models import BaseChatModel, init_chat_model

from agent.core.config import get_settings

# OpenCode Go 要求每个请求带稳定的会话标识，用于路由与缓存。
_SESSION_ID = f"network-teaching-agent-{uuid4()}"


@lru_cache
def get_llm() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(
        model=settings.deepseek.model,
        model_provider="deepseek",
        api_key=settings.deepseek.api_key,
        base_url=settings.deepseek.base_url,
        default_headers={
            "User-Agent": "network-teaching-agent/1.0",
            "x-opencode-session": _SESSION_ID,
        },
    )
