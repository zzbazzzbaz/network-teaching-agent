from fastapi import APIRouter

from app.api.v1.endpoints import auth, sandbox, sessions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sandbox.router)
api_router.include_router(sessions.router)
