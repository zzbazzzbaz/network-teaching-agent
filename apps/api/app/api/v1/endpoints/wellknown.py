from fastapi import APIRouter

from app.api.schemas.wellknown import JwksResponse
from app.core.security import jwks

router = APIRouter(tags=["well-known"])


@router.get("/.well-known/jwks.json", response_model=JwksResponse)
def get_jwks() -> JwksResponse:
    return JwksResponse.model_validate(jwks())
