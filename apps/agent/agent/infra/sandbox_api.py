import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
from e2b import Sandbox
from langgraph.config import get_config

from agent.core.config import get_settings

SANDBOX_RESOLUTION_TTL_SECONDS = 60.0


class SandboxApiError(RuntimeError):
    """API 无法提供当前用户可用沙箱。"""


@dataclass(frozen=True, slots=True)
class ResolvedSandbox:
    sandbox_id: str
    status: str


class SandboxApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        internal_token: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._internal_token = internal_token
        self._timeout_seconds = timeout_seconds

    def ensure_user_sandbox(self, user_id: str) -> ResolvedSandbox:
        if not self._internal_token:
            raise SandboxApiError("AGENT_INTERNAL_TOKEN 未配置")

        try:
            response = httpx.post(
                f"{self._base_url}/internal/sandbox/ensure",
                json={"user_id": user_id},
                headers={"X-Internal-Token": self._internal_token},
                timeout=self._timeout_seconds,
            )
        except (httpx.HTTPError, ValueError) as e:
            raise SandboxApiError("沙箱服务暂不可用，请稍后重试") from e

        if response.status_code != 200:
            raise SandboxApiError(_error_message(response))

        try:
            payload = response.json()
        except ValueError as e:
            raise SandboxApiError("沙箱服务返回了无效响应") from e

        sandbox_id = payload.get("sandbox_id") if isinstance(payload, dict) else None
        if not isinstance(sandbox_id, str) or not sandbox_id:
            raise SandboxApiError("沙箱服务未返回 sandbox_id")

        status = payload.get("status")
        return ResolvedSandbox(
            sandbox_id=sandbox_id,
            status=status if isinstance(status, str) else "running",
        )


class SandboxManager:
    """按用户解析、连接并缓存沙箱。

    AgsBackend 只需要提供当前用户 ID；API 调用、run 级缓存、
    E2B 连接和失效重试都封装在这里。
    """

    def __init__(self, *, api_client: SandboxApiClient | None = None) -> None:
        self._api_client = api_client
        self._sandboxes: dict[str, Sandbox] = {}
        self._resolved: dict[str, tuple[str, str | None, float]] = {}
        self._lock = threading.Lock()

    def get_sandbox(self, user_id: str) -> Sandbox:
        last_error: Exception | None = None
        for _ in range(2):
            sandbox_id = self._ensure_sandbox_id(user_id)
            with self._lock:
                cached = self._sandboxes.get(sandbox_id)
            if cached is not None:
                return cached

            try:
                sandbox = _connect_sandbox(sandbox_id)
            except Exception as e:
                last_error = e
                self.invalidate(user_id)
                continue

            with self._lock:
                return self._sandboxes.setdefault(sandbox_id, sandbox)

        raise RuntimeError("沙箱连接失败，请稍后重试") from last_error

    def invalidate(self, user_id: str) -> None:
        with self._lock:
            resolved = self._resolved.pop(user_id, None)
            if resolved is not None:
                self._sandboxes.pop(resolved[0], None)

    def _ensure_sandbox_id(self, user_id: str) -> str:
        run_id = _current_run_id()
        now = time.monotonic()
        with self._lock:
            cached = self._resolved.get(user_id)
            if (
                cached is not None
                and cached[1] == run_id
                and cached[2] > now
            ):
                return cached[0]

        try:
            resolved = self._api_client_instance().ensure_user_sandbox(user_id)
        except SandboxApiError as e:
            raise RuntimeError(str(e)) from e

        now = time.monotonic()
        with self._lock:
            previous = self._resolved.get(user_id)
            self._resolved[user_id] = (
                resolved.sandbox_id,
                run_id,
                now + SANDBOX_RESOLUTION_TTL_SECONDS,
            )
            if previous is not None and previous[0] != resolved.sandbox_id:
                self._sandboxes.pop(previous[0], None)
        return resolved.sandbox_id

    def _api_client_instance(self) -> SandboxApiClient:
        with self._lock:
            if self._api_client is None:
                settings = get_settings()
                self._api_client = SandboxApiClient(
                    base_url=settings.agent_api_base_url,
                    internal_token=settings.agent_internal_token,
                    timeout_seconds=settings.agent_api_timeout_seconds,
                )
            return self._api_client


def _current_run_id() -> str | None:
    try:
        run_id = get_config().get("run_id")
    except RuntimeError:
        return None
    return str(run_id) if run_id is not None and str(run_id) else None


def _connect_sandbox(sandbox_id: str) -> Sandbox:
    settings = get_settings()
    return Sandbox.connect(
        sandbox_id=sandbox_id, api_key=settings.e2b.api_key, domain=settings.e2b.domain
    )


def _error_message(response: httpx.Response) -> str:
    detail = ""
    try:
        payload: Any = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        detail = f": {payload['detail']}"
    return f"沙箱服务返回 {response.status_code}{detail}"
