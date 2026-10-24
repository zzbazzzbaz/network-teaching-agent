import asyncio
from functools import lru_cache
from typing import Any

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


@auth.authenticate
async def authenticate(
    authorization: str | None = None,
) -> Auth.types.MinimalUserDict:
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


@auth.on
async def deny_unhandled(ctx: Auth.types.AuthContext, value: object) -> None:
    raise Auth.exceptions.HTTPException(status_code=403, detail="禁止访问该资源")
