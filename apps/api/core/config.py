from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class _Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
    )


class E2BSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="E2B_")

    domain: str
    api_key: str


class AGSSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="AGS_")

    image_id: str
    sandbox_timeout_seconds: int


class COSSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="COS_")

    secret_id: str
    secret_key: str
    region: str
    bucket: str


class DBSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="DB_")

    database_url: str


class Settings(_Base):
    e2b: E2BSettings = Field(default_factory=E2BSettings)
    ags: AGSSettings = Field(default_factory=AGSSettings)
    cos: COSSettings = Field(default_factory=COSSettings)
    db: DBSettings = Field(default_factory=DBSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
