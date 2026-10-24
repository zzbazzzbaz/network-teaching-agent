from functools import lru_cache

from langchain.chat_models import BaseChatModel, init_chat_model

from core.config import get_settings


@lru_cache
def get_llm() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(
        model=settings.deepseek_model,
        model_provider="deepseek",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
