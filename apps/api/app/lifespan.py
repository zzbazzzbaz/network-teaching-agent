from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  确保建表模型已注册
from app.core.config import Settings
from app.core.database import create_all, create_db_engine, create_session_factory


def build_lifespan(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        engine = create_db_engine(settings.db.database_url)
        create_all(engine)
        application.state.session_factory = create_session_factory(engine)
        try:
            yield
        finally:
            engine.dispose()

    return lifespan
