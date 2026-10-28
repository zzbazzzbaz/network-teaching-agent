import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.internal.router import router as internal_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.wellknown import router as wellknown_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.lifespan import build_lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings if settings is not None else get_settings()
    application = FastAPI(
        title="computer-network-agent-api",
        version="0.1.0",
        lifespan=build_lifespan(resolved_settings),
    )
    origins = resolved_settings.cors_origins_list
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    application.state.settings = resolved_settings
    register_error_handlers(application)
    # 内部接口保留在 /internal，不挂 /api/v1，避免被 nginx 的 /api/ 转发到公网。
    application.include_router(internal_router)
    application.include_router(api_router, prefix="/api/v1")
    application.include_router(wellknown_router)
    application.include_router(health_router)
    return application


app = create_app()
