from app.api.schemas.base import ApiResponse


class JwkResponse(ApiResponse):
    kty: str
    kid: str
    use: str
    alg: str
    n: str
    e: str


class JwksResponse(ApiResponse):
    keys: list[JwkResponse]
