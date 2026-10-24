"""E2E 专用 API 启动器：SQLite + 固定测试账号，避免污染开发数据库。"""

import os
import sys
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / ".e2e.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DB_DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ.setdefault("JWT_ISSUER", "computer-network-agent")
os.environ.setdefault("JWT_AUDIENCE", "agent")

KEYS_DIR = ROOT / ".keys"
PRIVATE_KEY_PATH = KEYS_DIR / "jwt_private.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "jwt_public.pem"


def _ensure_keys() -> None:
    if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
        return
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    PUBLIC_KEY_PATH.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    PRIVATE_KEY_PATH.chmod(0o600)


def _seed_users(session_factory: sessionmaker[Session]) -> None:
    from core.security import hash_password
    from repositories.user_repository import user_repository

    accounts = {
        "e2e_student": "e2e-password-123",
        "e2e_other": "e2e-password-456",
    }
    with session_factory() as session:
        for username, password in accounts.items():
            if user_repository.get_by_username(session, username) is None:
                user_repository.create(
                    session,
                    username=username,
                    password_hash=hash_password(password),
                )


def main() -> None:
    _ensure_keys()

    import uvicorn

    from core.config import get_settings
    from core.database import create_all, create_db_engine, create_session_factory
    from main import create_app

    settings = get_settings()
    engine = create_db_engine(settings.db.database_url)
    create_all(engine)
    session_factory = create_session_factory(engine)
    _seed_users(session_factory)

    port = int(os.environ.get("E2E_API_PORT", "8000"))
    app = create_app(settings)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
