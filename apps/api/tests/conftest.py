import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.database import create_db_engine
from app.core.security import hash_password
from app.models.user import Users

API_DIR = Path(__file__).resolve().parents[1]
INTERNAL_TOKEN = "test-internal-token"


@pytest.fixture(autouse=True)
def internal_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_INTERNAL_TOKEN", INTERNAL_TOKEN)


@pytest.fixture(scope="session")
def jwt_key_paths(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    directory = tmp_path_factory.mktemp("jwt-keys")
    private_path = directory / "jwt_private.pem"
    public_path = directory / "jwt_public.pem"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return str(private_path), str(public_path)


@pytest.fixture
def database_url() -> Iterator[str]:
    """每个测试使用独立的 Postgres schema，避免污染开发数据。"""
    settings = get_settings()
    schema = f"test_{uuid.uuid4().hex}"
    admin_engine = create_db_engine(settings.db.database_url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        url = make_url(settings.db.database_url)
        yield url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(
            hide_password=False
        )
    finally:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def _run_migrations() -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
    jwt_key_paths: tuple[str, str],
) -> Iterator[TestClient]:
    private_path, public_path = jwt_key_paths
    monkeypatch.setenv("DB_DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", private_path)
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", public_path)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    get_settings.cache_clear()
    _run_migrations()

    from app.main import create_app

    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def create_user(client: TestClient) -> Callable[..., Users]:
    def _create(
        username: str = "alice",
        password: str = "password123",
        status: bool = True,
    ) -> Users:
        with cast(FastAPI, client.app).state.session_factory() as session:
            user = Users(
                username=username,
                password_hash=hash_password(password),
                status=status,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    return _create
