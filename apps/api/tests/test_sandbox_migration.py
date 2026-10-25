import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings

API_DIR = Path(__file__).resolve().parents[1]


def test_sandbox_lifecycle_migration_backfills_existing_records(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(API_DIR / "alembic.ini"))

    user_id = uuid.uuid4()
    created_at = datetime.now(UTC) - timedelta(days=2)
    updated_at = datetime.now(UTC) - timedelta(hours=1)
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    try:
        command.upgrade(config, "0002_user_sandboxes")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users
                        (user_id, username, password_hash, status, created_at, updated_at)
                    VALUES
                        (:user_id, :username, :password_hash, true, :created_at, :updated_at)
                    """
                ),
                {
                    "user_id": user_id,
                    "username": "legacy-sandbox-user",
                    "password_hash": "hash",
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO user_sandboxes
                        (user_id, sandbox_id, expires_at, created_at, updated_at)
                    VALUES
                        (:user_id, :sandbox_id, :expires_at, :created_at, :updated_at)
                    """
                ),
                {
                    "user_id": user_id,
                    "sandbox_id": "legacy-sandbox",
                    "expires_at": expires_at,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT status, last_active_at, paused_at, hard_destroy_at
                    FROM user_sandboxes
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).one()

        assert row.status == "running"
        assert row.paused_at is None
        assert abs((row.last_active_at - updated_at).total_seconds()) < 1
        assert abs(
            (row.hard_destroy_at - (created_at + timedelta(days=7))).total_seconds()
        ) < 1
    finally:
        get_settings.cache_clear()
