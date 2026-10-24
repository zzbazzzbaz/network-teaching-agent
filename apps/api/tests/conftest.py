from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import Users


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
def client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    jwt_key_paths: tuple[str, str],
) -> Iterator[TestClient]:
    private_path, public_path = jwt_key_paths
    monkeypatch.setenv("DB_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", private_path)
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", public_path)
    monkeypatch.setenv("JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("JWT_AUDIENCE", "test-audience")
    get_settings.cache_clear()

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
