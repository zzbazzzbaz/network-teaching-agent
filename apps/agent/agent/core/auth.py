"""LangGraph 鉴权：平台 JWT 本地验签（RS256 + JWKS 缓存）+ 资源级用户隔离。

- 公钥按 kid 缓存，日常请求不调外部服务；
- 认证只回答「是谁」；资源的读写授权由 @auth.on 处理器决定。
- LangGraph 对未注册的 resource/action 是 fail-open，因此必须有全局兜底拒绝。
"""

import asyncio
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError
from langgraph_sdk import Auth

from agent.core.config import get_settings

auth = Auth()

# 协议常量：必须与 API 端 app/core/constants.py 保持一致。
JWT_ISSUER = "computer-network-agent"
JWT_AUDIENCE = "agent"


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
        raise Auth.exceptions.HTTPException(status_code=401, detail="缺少登录 token，请先登录")
    token = authorization[7:].strip()
    try:
        payload = await asyncio.to_thread(_verify, token)
    except PyJWKClientConnectionError as e:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="鉴权服务不可用，请稍后重试"
        ) from e
    except jwt.PyJWTError as e:
        raise Auth.exceptions.HTTPException(status_code=401, detail="登录已失效，请重新登录") from e
    except Exception as e:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="鉴权服务不可用，请稍后重试"
        ) from e
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
    """发起 run：过滤非本人会话；线程若由 run 隐式创建，同样写入 owner。"""
    metadata = value.get("metadata")
    if metadata is None:
        metadata = {}
        value["metadata"] = metadata
    metadata["owner"] = ctx.user.identity
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
    """其余会话动作（read / delete / search 等）按 owner 过滤，非本人视为不存在。"""
    return {"owner": ctx.user.identity}


@auth.on
async def deny_unhandled(ctx: Auth.types.AuthContext, value: object) -> None:
    """未显式放行的资源（assistants / crons / store 等）默认拒绝。"""
    raise Auth.exceptions.HTTPException(status_code=403, detail="禁止访问该资源")
