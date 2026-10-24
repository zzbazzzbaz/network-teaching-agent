from functools import lru_cache

from langchain.chat_models import BaseChatModel, init_chat_model

from core.config import get_settings


@lru_cache
def get_llm() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(
        model=settings.deepseek.model,
        model_provider="deepseek",
        api_key=settings.deepseek.api_key,
        base_url=settings.deepseek.base_url,
    )
