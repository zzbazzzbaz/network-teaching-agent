from typing import Any

from fastapi import APIRouter

from app.core.security import jwks

router = APIRouter(tags=["well-known"])


@router.get("/.well-known/jwks.json")
def get_jwks() -> dict[str, Any]:
    return jwks()
