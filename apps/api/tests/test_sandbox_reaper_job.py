from typing import cast

from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.job.sandbox_reaper import run_reaper_job
from app.job.scheduler import SANDBOX_REAPER_JOB_ID, build_scheduler


def test_reaper_runs_once(client: TestClient) -> None:
    application = cast(FastAPI, client.app)
    settings = cast(Settings, application.state.settings)
    session_factory = cast(sessionmaker[Session], application.state.session_factory)

    stats = run_reaper_job(
        settings=settings,
        session_factory=session_factory,
    )

    assert stats.paused == 0
    assert stats.destroyed == 0
    assert stats.cleared == 0
    assert stats.failed == 0


def test_scheduler_registers_reaper_job(client: TestClient) -> None:
    application = cast(FastAPI, client.app)
    settings = cast(Settings, application.state.settings)
    session_factory = cast(sessionmaker[Session], application.state.session_factory)

    scheduler = build_scheduler(settings=settings, session_factory=session_factory)
    scheduler.start(paused=True)
    try:
        job = scheduler.get_job(SANDBOX_REAPER_JOB_ID)

        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)
        assert job.trigger.interval.total_seconds() == settings.scheduler.reaper_interval_seconds
        assert job.max_instances == 1
        assert job.coalesce is True
    finally:
        scheduler.shutdown(wait=False)
