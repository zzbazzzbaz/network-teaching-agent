from __future__ import annotations

import threading

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

from agent.infra.ags import connect_sandbox

DEFAULT_WORK_DIR = "/home/user/workspace"
MISSING_SANDBOX_ID = "sandbox_id 未传入，请先启动沙箱"


class AgsBackend(BaseSandbox):
    enable_capture_offload = True

    def __init__(self, *, work_dir: str = DEFAULT_WORK_DIR) -> None:
        self._default_timeout = 300
        self._user = "user"
        self._work_dir = work_dir
        self._sandboxes: dict[str, Sandbox] = {}
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        return self._sandbox_id() or "sandbox"

    def _sandbox_id(self) -> str | None:
        try:
            config = get_config()
        except RuntimeError:
            return None

        configurable = config.get("configurable")
        if not isinstance(configurable, dict):
            return None

        sandbox_id = configurable.get("sandbox_id")
        if isinstance(sandbox_id, str) and sandbox_id:
            return sandbox_id
        return None

    def _get_sandbox(self) -> Sandbox:
        sandbox_id = self._sandbox_id()
        if sandbox_id is None:
            raise RuntimeError(MISSING_SANDBOX_ID)

        with self._lock:
            sandbox = self._sandboxes.get(sandbox_id)
            if sandbox is None:
                sandbox = connect_sandbox(sandbox_id)
                self._sandboxes[sandbox_id] = sandbox
            return sandbox

    def _drop_sandbox(self) -> None:
        sandbox_id = self._sandbox_id()
        if sandbox_id is None:
            return
        with self._lock:
            self._sandboxes.pop(sandbox_id, None)

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
