from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError


def register_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @application.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        messages: list[str] = []
        for error in exc.errors():
            location = ".".join(
                str(part)
                for part in error["loc"]
                if part not in {"body", "query", "path"}
            )
            message = str(error["msg"]).removeprefix("Value error, ")
            messages.append(f"{location}: {message}" if location else message)
        detail = "；".join(messages) or "请求参数校验失败"
        return JSONResponse(status_code=422, content={"detail": detail})
