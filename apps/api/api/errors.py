from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.exceptions import AppError


def register_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})
