import threading
import time
from collections.abc import Mapping
from typing import Any

from deepagents.backends.protocol import ExecuteResponse, FileDownloadResponse, FileUploadResponse
from deepagents.backends.sandbox import BaseSandbox
from e2b import (
    CommandExitException,
    CommandResult,
    FileNotFoundException,
    Sandbox,
    SandboxException,
)
from langgraph.config import get_config

from agent.core.config import get_settings
from agent.infra.sandbox_api import SandboxApiClient, SandboxApiError

DEFAULT_WORK_DIR = "/root/workspace"
DEFAULT_USER = "root"
SANDBOX_RESOLUTION_TTL_SECONDS = 60.0


class AgsBackend(BaseSandbox):
    enable_capture_offload = True

    def __init__(
        self,
        *,
        work_dir: str = DEFAULT_WORK_DIR,
        user: str = DEFAULT_USER,
    ) -> None:
        self._default_timeout = 300
        self._user = user
        self._work_dir = work_dir
        self._sandboxes: dict[str, Sandbox] = {}
        self._resolved: dict[str, tuple[str, str | None, float]] = {}
        self._api_client: SandboxApiClient | None = None
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        try:
            return f"ags:{_current_user_id()}"
        except RuntimeError:
            return "ags:unauthenticated"

    def _get_sandbox(self) -> Sandbox:
        last_error: Exception | None = None
        for _ in range(2):
            sandbox_id = self._ensure_sandbox_id()
            with self._lock:
                cached = self._sandboxes.get(sandbox_id)
            if cached is not None:
                return cached

            try:
                sandbox = _connect_sandbox(sandbox_id)
            except Exception as e:
                last_error = e
                self._drop_sandbox()
                continue

            with self._lock:
                return self._sandboxes.setdefault(sandbox_id, sandbox)

        raise RuntimeError("沙箱连接失败，请稍后重试") from last_error

    def _ensure_sandbox_id(self) -> str:
        user_id = _current_user_id()
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

    def _drop_sandbox(self) -> None:
        try:
            user_id = _current_user_id()
        except RuntimeError:
            return
        with self._lock:
            resolved = self._resolved.pop(user_id, None)
            if resolved is not None:
                self._sandboxes.pop(resolved[0], None)

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        timeout = self._default_timeout if timeout is None else timeout
        try:
            result: CommandResult = self._get_sandbox().commands.run(
                command,
                cwd=self._work_dir,
                timeout=timeout,
                user=self._user,
            )
        except CommandExitException as e:
            result = e
        except RuntimeError as e:
            return ExecuteResponse(output=str(e), exit_code=None)
        except SandboxException as e:
            self._drop_sandbox()
            return ExecuteResponse(
                output=f"{type(e).__name__}: {e}",
                exit_code=None,
            )
        return ExecuteResponse(
            output=_combine(result.stdout, result.stderr),
            exit_code=result.exit_code,
        )

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        try:
            sandbox = self._get_sandbox()
        except RuntimeError as e:
            return [FileUploadResponse(path=path, error=str(e)) for path, _ in files]

        responses: list[FileUploadResponse] = []
        for path, data in files:
            try:
                sandbox.files.write(path, data, user=self._user)
                responses.append(FileUploadResponse(path=path))
            except SandboxException as e:
                responses.append(FileUploadResponse(path=path, error=_file_error(e)))
        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        try:
            sandbox = self._get_sandbox()
        except RuntimeError as e:
            return [FileDownloadResponse(path=path, error=str(e)) for path in paths]

        responses: list[FileDownloadResponse] = []
        for path in paths:
            try:
                content = sandbox.files.read(path, format="bytes", user=self._user)
                responses.append(FileDownloadResponse(path=path, content=bytes(content)))
            except SandboxException as e:
                responses.append(FileDownloadResponse(path=path, error=_file_error(e)))
        return responses


def _current_user_id() -> str:
    configurable = _configurable()
    user_id = configurable.get("langgraph_auth_user_id")
    if user_id is not None and str(user_id):
        return str(user_id)

    user = configurable.get("langgraph_auth_user")
    identity: Any
    if isinstance(user, Mapping):
        identity = user.get("identity")
    else:
        identity = getattr(user, "identity", None)
    if identity is not None and str(identity):
        return str(identity)

    raise RuntimeError("未认证用户，无法解析沙箱")


def _current_run_id() -> str | None:
    try:
        config = get_config()
    except RuntimeError:
        return None
    run_id = config.get("run_id")
    if run_id is not None and str(run_id):
        return str(run_id)
    metadata = config.get("metadata")
    if isinstance(metadata, Mapping):
        run_id = metadata.get("run_id")
        if run_id is not None and str(run_id):
            return str(run_id)
    return None


def _configurable() -> Mapping[str, Any]:
    try:
        config = get_config()
    except RuntimeError:
        return {}
    configurable = config.get("configurable")
    if isinstance(configurable, Mapping):
        return configurable
    return {}


def _connect_sandbox(sandbox_id: str) -> Sandbox:
    settings = get_settings()
    return Sandbox.connect(
        sandbox_id=sandbox_id, api_key=settings.e2b.api_key, domain=settings.e2b.domain
    )


def _file_error(e: Exception) -> str:
    if isinstance(e, FileNotFoundException):
        return "file_not_found"

    msg = str(e).lower()
    if "is a directory" in msg:
        return "is_directory"
    if "permission denied" in msg or "access denied" in msg:
        return "permission_denied"
    if "invalid path" in msg or "invalid argument" in msg:
        return "invalid_path"
    return f"{type(e).__name__}: {e}"


def _combine(stdout: str, stderr: str) -> str:
    """文本合并"""
    out = (stdout or "").rstrip("\n")
    if stderr:
        err = "\n".join(f"[stderr] {line}" for line in stderr.splitlines())
        out = f"{out}\n{err}" if out else err
    return out or "<no output>"
