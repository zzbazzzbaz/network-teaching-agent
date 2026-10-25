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
    get_langfuse()
    return CallbackHandler()
