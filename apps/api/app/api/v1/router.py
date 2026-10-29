from fastapi import APIRouter

from app.api.v1.endpoints import auth, files, memory, question_bank, sandbox, sessions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(sandbox.router)
api_router.include_router(sessions.router)
api_router.include_router(question_bank.router)
api_router.include_router(memory.router)
