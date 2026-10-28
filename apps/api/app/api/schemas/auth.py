import uuid

from app.api.schemas.base import ApiRequest, ApiResponse


class LoginBody(ApiRequest):
    username: str
    password: str


class RefreshBody(ApiRequest):
    refresh_token: str


class AuthResponse(ApiResponse):
    user_id: uuid.UUID
    username: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserResponse(ApiResponse):
    user_id: uuid.UUID
    username: str
