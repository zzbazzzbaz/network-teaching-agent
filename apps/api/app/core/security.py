"""自建认证：RS256 JWT 签发/验签、JWKS、bcrypt 口令。"""

import hashlib
import json
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import bcrypt
import jwt
from jwt import algorithms

from app.core.config import get_settings
from app.core.constants import (
    ACCESS_TOKEN_TYPE,
    JWT_ALGORITHM,
    REFRESH_TOKEN_TYPE,
)
from app.core.exceptions import UnauthorizedError, ValidationError


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


@lru_cache(maxsize=8)
def _private_key(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


@lru_cache(maxsize=8)
def _public_key(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _private_key_value() -> str:
    return _private_key(get_settings().jwt.private_key_path)


def _public_key_value() -> str:
    return _public_key(get_settings().jwt.public_key_path)


@lru_cache(maxsize=8)
def _key_id(public_key: str) -> str:
    return hashlib.sha256(public_key.encode("utf-8")).hexdigest()[:16]


def key_id() -> str:
    return _key_id(_public_key_value())


def _encode_token(user_id: str, token_type: str, ttl_seconds: int) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "iss": settings.jwt.issuer,
        "aud": settings.jwt.audience,
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": uuid.uuid4().hex,
        "typ": token_type,
    }
    return jwt.encode(
        payload,
        _private_key_value(),
        algorithm=JWT_ALGORITHM,
        headers={"kid": key_id()},
    )


def create_access_token(user_id: str) -> tuple[str, int]:
    """返回 (token, 有效秒数)。"""
    ttl = get_settings().jwt.access_token_ttl_seconds
    return _encode_token(user_id, ACCESS_TOKEN_TYPE, ttl), ttl


def create_refresh_token(user_id: str) -> str:
    return _encode_token(
        user_id,
        REFRESH_TOKEN_TYPE,
        get_settings().jwt.refresh_token_ttl_seconds,
    )


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            _public_key_value(),
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt.audience,
            issuer=settings.jwt.issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise UnauthorizedError("令牌无效或已过期") from e
    if payload.get("typ") != expected_type:
        raise UnauthorizedError("令牌类型不正确")
    return payload


def _decode_user_id(token: str, *, expected_type: str) -> uuid.UUID:
    payload = decode_token(token, expected_type=expected_type)
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise UnauthorizedError("令牌缺少用户标识")
    try:
        return uuid.UUID(user_id)
    except ValueError as e:
        raise UnauthorizedError("令牌中的用户标识无效") from e


def decode_access_token(token: str) -> uuid.UUID:
    return _decode_user_id(token, expected_type=ACCESS_TOKEN_TYPE)


def decode_refresh_token(token: str) -> uuid.UUID:
    return _decode_user_id(token, expected_type=REFRESH_TOKEN_TYPE)


def jwks() -> dict[str, Any]:
    """平台 JWKS（供 Agent 本地验签）。"""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    public_key = serialization.load_pem_public_key(_public_key_value().encode("utf-8"))
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValidationError("JWT 公钥必须是 RSA 公钥")
    jwk = json.loads(algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk.update({"kid": key_id(), "use": "sig", "alg": JWT_ALGORITHM})
    return {"keys": [jwk]}
