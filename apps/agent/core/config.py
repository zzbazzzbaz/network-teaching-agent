from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


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


class Settings(_Base):
    deepseek: DeepSeekSettings = Field(default_factory=DeepSeekSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    e2b: E2BSettings = Field(default_factory=E2BSettings)

    # 平台 JWT（本地 via JWKS 验签）
    jwks_url: str = "http://127.0.0.1:8000/.well-known/jwks.json"
    # 进程级覆盖（E2E / 多环境部署用；优先于 .env 中的 JWKS_URL）
    jwks_url_override: str | None = None
    jwt_issuer: str = "computer-network-agent"
    jwt_audience: str = "agent"

    @property
    def resolved_jwks_url(self) -> str:
        return self.jwks_url_override or self.jwks_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
