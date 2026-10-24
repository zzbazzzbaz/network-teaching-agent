import uuid

from pydantic import BaseModel


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    user_id: uuid.UUID
    username: str
