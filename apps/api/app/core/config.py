from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
API_DIR = Path(__file__).resolve().parents[2]


class _Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class E2BSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="E2B_")

    domain: str
    api_key: str


class AGSSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="AGS_")

    tool_name: str
    sandbox_timeout_seconds: int


class DBSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="DB_")

    database_url: str


class JWTSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    private_key_path: str
    public_key_path: str
    issuer: str
    audience: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int

    @field_validator("private_key_path", "public_key_path")
    @classmethod
    def _resolve_key_path(cls, value: str) -> str:
        path = Path(value).expanduser()
        return str(path if path.is_absolute() else API_DIR / path)


class Settings(_Base):
    e2b: E2BSettings = Field(default_factory=E2BSettings)
    ags: AGSSettings = Field(default_factory=AGSSettings)
    db: DBSettings = Field(default_factory=DBSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)

    cors_origins: str

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
