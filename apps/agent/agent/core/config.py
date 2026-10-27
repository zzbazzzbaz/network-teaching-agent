from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class _Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DeepSeekSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="DEEPSEEK_")

    api_key: str
    base_url: str
    model: str


class LangfuseSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="LANGFUSE_")

    secret_key: str
    public_key: str
    base_url: str


class E2BSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="E2B_")

    domain: str
    api_key: str


class JWTSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    jwks_url: str


class Settings(_Base):
    deepseek: DeepSeekSettings = Field(default_factory=DeepSeekSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    e2b: E2BSettings = Field(default_factory=E2BSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)

    agent_api_base_url: str = Field(min_length=1)
    agent_internal_token: str = Field(min_length=1)
    agent_api_timeout_seconds: float = 15.0
    agent_dev_user_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
