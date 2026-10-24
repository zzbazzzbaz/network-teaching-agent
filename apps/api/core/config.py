from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
API_DIR = Path(__file__).resolve().parents[1]


class _Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class E2BSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="E2B_")

    domain: str = ""
    api_key: str = ""


class AGSSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="AGS_")

    tool_name: str = ""
    sandbox_timeout_seconds: int = 300


class DBSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="DB_")

    database_url: str


class Settings(_Base):
    e2b: E2BSettings = Field(default_factory=E2BSettings)
    ags: AGSSettings = Field(default_factory=AGSSettings)
    db: DBSettings = Field(default_factory=DBSettings)

    # 登录态：API 持私钥签发，Agent 通过 JWKS 本地验签。
    jwt_private_key_path: str = str(API_DIR / ".keys" / "jwt_private.pem")
    jwt_public_key_path: str = str(API_DIR / ".keys" / "jwt_public.pem")
    jwt_issuer: str = "computer-network-agent"
    jwt_audience: str = "agent"
    access_token_ttl_seconds: int = 30 * 60
    refresh_token_ttl_seconds: int = 7 * 24 * 60 * 60

    cors_origins: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
