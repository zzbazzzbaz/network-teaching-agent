from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.job.sandbox_reaper import run_reaper


def test_reaper_runs_once(client: TestClient) -> None:
    application = cast(FastAPI, client.app)
    settings = cast(Settings, application.state.settings)
    session_factory = cast(sessionmaker[Session], application.state.session_factory)

    stats = run_reaper(
        settings=settings,
        session_factory=session_factory,
    )

    assert stats.paused == 0
    assert stats.destroyed == 0
    assert stats.cleared == 0
    assert stats.failed == 0
