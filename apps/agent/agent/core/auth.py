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
    """会话创建：把 owner 写入 metadata；返回 owner 过滤保护 if_exists 的已有会话。"""
    metadata = value.get("metadata")
    if metadata is None:
        metadata = {}
        value["metadata"] = metadata
    metadata["owner"] = ctx.user.identity
    return {"owner": ctx.user.identity}


@auth.on.threads.create_run
async def stamp_run_owner(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.create_run.value,
) -> dict[str, str]:
    """发起 run：过滤非本人会话；写入 owner 与 Langfuse 关联字段。

    `thread_id` 是 LangGraph 的 checkpoint key，Langfuse 不会自动把它当作 session，
    这里显式映射；用户身份以服务端鉴权结果为准，覆盖客户端可能传入的同名字段。
    """
    metadata = value.get("metadata")
    if metadata is None:
        metadata = {}
        value["metadata"] = metadata
    metadata["owner"] = ctx.user.identity
    metadata["langfuse_user_id"] = ctx.user.identity
    thread_id = value.get("thread_id")
    if thread_id is not None:
        metadata["langfuse_session_id"] = str(thread_id)
    return {"owner": ctx.user.identity}


@auth.on.threads.update
async def pin_thread_owner(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.update.value,
) -> dict[str, str]:
    """更新会话：强制保留 owner，防止通过 metadata 把会话转给他人。"""
    metadata = value.get("metadata")
    if metadata is None:
        metadata = {}
        value["metadata"] = metadata
    metadata["owner"] = ctx.user.identity
    return {"owner": ctx.user.identity}


@auth.on.threads
async def filter_own_threads(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.value,
) -> dict[str, str]:
    return {"owner": ctx.user.identity}


@auth.on
async def deny_unhandled(ctx: Auth.types.AuthContext, value: object) -> None:
    raise Auth.exceptions.HTTPException(status_code=403, detail="禁止访问该资源")
