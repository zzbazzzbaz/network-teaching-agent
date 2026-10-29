"""与业务无关的 HTTP 工具：共享 client、JSON 请求和上游错误分类。"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class UpstreamError(RuntimeError):
    """上游 HTTP 错误基类。"""


class UpstreamUnavailable(UpstreamError):
    """连接失败、超时或上游 5xx。"""


class UpstreamAuthError(UpstreamError):
    """上游返回 401/403。"""


class UpstreamContractError(UpstreamError):
    """上游返回了非法 JSON 或空响应。"""


class UpstreamStatusError(UpstreamError):
    """其他 4xx；调用方可以按 status_code 处理。"""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code


def build_http_client(
    *,
    base_url: str,
    timeout_seconds: float,
    headers: Mapping[str, str] | None = None,
) -> httpx.Client:
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=httpx.Timeout(timeout_seconds),
        headers=dict(headers or {}),
        trust_env=False,
    )


def request_json(
    http: httpx.Client,
    *,
    method: str,
    path: str,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    json: Mapping[str, Any] | None = None,
) -> object:
    started = time.perf_counter()
    try:
        response = http.request(
            method,
            path,
            headers=dict(headers or {}),
            params=params,
            json=json,
        )
    except httpx.TimeoutException as e:
        _log_failure("timeout", method, path, started)
        raise UpstreamUnavailable("上游请求超时") from e
    except httpx.HTTPError as e:
        _log_failure("connection", method, path, started)
        raise UpstreamUnavailable("上游请求失败") from e

    if response.status_code in {401, 403}:
        logger.error(
            "upstream auth failed method=%s path=%s status=%s elapsed_ms=%.1f",
            method,
            path,
            response.status_code,
            _elapsed_ms(started),
        )
        raise UpstreamAuthError("上游凭证无效")
    if response.status_code >= 500:
        logger.warning(
            "upstream unavailable method=%s path=%s status=%s elapsed_ms=%.1f",
            method,
            path,
            response.status_code,
            _elapsed_ms(started),
        )
        raise UpstreamUnavailable(f"上游返回 {response.status_code}")
    if response.status_code >= 400:
        logger.warning(
            "upstream request rejected method=%s path=%s status=%s elapsed_ms=%.1f",
            method,
            path,
            response.status_code,
            _elapsed_ms(started),
        )
        raise UpstreamStatusError(response.status_code, response.text[:200])
    if response.status_code == 204:
        return None
    if not response.content:
        logger.error(
            "upstream returned empty body method=%s path=%s status=%s",
            method,
            path,
            response.status_code,
        )
        raise UpstreamContractError("上游返回空响应")

    try:
        return response.json()
    except ValueError as e:
        logger.error(
            "upstream returned invalid json method=%s path=%s status=%s",
            method,
            path,
            response.status_code,
        )
        raise UpstreamContractError("上游返回非 JSON") from e


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _log_failure(reason: str, method: str, path: str, started: float) -> None:
    logger.warning(
        "upstream %s method=%s path=%s elapsed_ms=%.1f",
        reason,
        method,
        path,
        _elapsed_ms(started),
    )
