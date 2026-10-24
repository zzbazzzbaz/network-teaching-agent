from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_base_url: str

    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str

    e2b_domain: str
    e2b_api_key: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
