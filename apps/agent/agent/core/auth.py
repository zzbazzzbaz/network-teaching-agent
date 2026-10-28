import asyncio
import secrets
import uuid
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, NoReturn

import jwt
from jwt import PyJWKClient
from langgraph_sdk import Auth

from agent.core.config import get_settings
from agent.core.constants import JWT_AUDIENCE, JWT_ISSUER

auth = Auth()


@lru_cache
def _jwks_client() -> PyJWKClient:
    settings = get_settings()
    return PyJWKClient(settings.jwt.jwks_url, cache_keys=True, lifespan=300)


@auth.authenticate
async def authenticate(
    headers: Mapping[bytes, bytes] | None = None,
    path: str = "",
    authorization: str | None = None,
) -> Auth.types.MinimalUserDict:
    internal_identity = _internal_identity(headers or {}, path=path)
    if internal_identity is not None:
        return {"identity": internal_identity}

    if not authorization or not authorization.lower().startswith("bearer "):
        raise Auth.exceptions.HTTPException(status_code=401)
    token = authorization[7:].strip()
    try:
        payload = await asyncio.to_thread(_verify, token)
    except jwt.PyJWTError as e:
        raise Auth.exceptions.HTTPException(status_code=401) from e
    except Exception as e:
        raise Auth.exceptions.HTTPException(status_code=503) from e
    return {"identity": payload["sub"]}


@auth.on.threads.create
async def stamp_thread_owner(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.create.value,
) -> dict[str, str]:
    filters = {"owner": ctx.user.identity}
    value.setdefault("metadata", {}).update(filters)
    return filters


@auth.on.threads.create_run
async def stamp_run_owner(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.create_run.value,
) -> dict[str, str]:
    thread_id = value.get("thread_id")
    if thread_id is None:
        raise Auth.exceptions.HTTPException(
            status_code=403, detail="禁止通过 run 创建临时会话，请先创建会话"
        )

    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    metadata["langfuse_user_id"] = ctx.user.identity
    metadata["langfuse_session_id"] = str(thread_id)
    return filters


@auth.on.threads.update
async def pin_thread_owner(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.update.value,
) -> dict[str, str]:
    filters = {"owner": ctx.user.identity}
    value.setdefault("metadata", {}).update(filters)
    return filters


@auth.on.threads
async def filter_own_threads(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.value,
) -> dict[str, str]:
    return {"owner": ctx.user.identity}


@auth.on.store
async def scope_store(
    ctx: Auth.types.AuthContext,
    value: dict[str, Any],
) -> None:
    def _deny_store(detail: str) -> NoReturn:
        raise Auth.exceptions.HTTPException(status_code=403, detail=detail)

    if ctx.action not in {"get", "search"}:
        _deny_store(f"记忆 Store 不支持 {ctx.action}")

    expected = ("users", ctx.user.identity, "memory")
    namespace = value.get("namespace")
    if not isinstance(namespace, (list, tuple)) or tuple(namespace) != expected:
        _deny_store("只允许访问当前用户的记忆 namespace")

    if ctx.action == "get":
        key = value.get("key")
        if (
            not isinstance(key, str)
            or not key.startswith("/")
            or "\\" in key
            or "\x00" in key
            or ".." in key.split("/")
        ):
            _deny_store("非法记忆文件路径")

    value["namespace"] = expected


@auth.on
async def deny_unhandled(ctx: Auth.types.AuthContext, value: object) -> None:
    raise Auth.exceptions.HTTPException(status_code=403, detail="禁止访问该资源")


def _verify(token: str) -> dict[str, Any]:
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iat", "sub"]},
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("令牌类型不正确")
    return payload


def _internal_identity(
    headers: Mapping[bytes, bytes],
    *,
    path: str,
) -> str | None:
    def _header(headers: Mapping[bytes, bytes], name: bytes) -> str | None:
        value = headers.get(name)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return None

    def _is_store_path(path: str) -> bool:
        return path == "/store" or path.startswith("/store/")

    if not _is_store_path(path):
        return None

    token = _header(headers, b"x-internal-token")
    user_id = _header(headers, b"x-user-id")
    if not token or not user_id:
        raise Auth.exceptions.HTTPException(status_code=401, detail="缺少内部凭证")
    if not secrets.compare_digest(token, get_settings().server.auth_token):
        raise Auth.exceptions.HTTPException(status_code=403, detail="内部凭证无效")
    try:
        return str(uuid.UUID(user_id))
    except ValueError as e:
        raise Auth.exceptions.HTTPException(status_code=401, detail="X-User-Id 无效") from e
