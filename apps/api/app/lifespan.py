import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

import app.models  # noqa: F401  确保模型已注册
from app.core.config import Settings
from app.core.database import create_db_engine, create_session_factory
from app.job.scheduler import build_scheduler

logger = logging.getLogger(__name__)


def build_lifespan(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        engine = create_db_engine(settings.db.database_url)
        session_factory = create_session_factory(engine)
        application.state.session_factory = session_factory

        scheduler: BackgroundScheduler | None = None
        if settings.scheduler.enabled:
            scheduler = build_scheduler(settings=settings, session_factory=session_factory)
            scheduler.start()
            logger.info(
                "sandbox reaper 调度已启动，间隔 %s 秒",
                settings.scheduler.reaper_interval_seconds,
            )
        application.state.scheduler = scheduler

        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)
            engine.dispose()

    return lifespan
