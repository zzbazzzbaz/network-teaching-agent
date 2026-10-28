from app.api.schemas.base import ApiResponse


class HealthResponse(ApiResponse):
    status: str
