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

from agent.core.config import get_settings
from agent.infra.sandbox_api import ensure_sandbox_id

DEFAULT_WORK_DIR = "/root/workspace"
DEFAULT_USER = "root"


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
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        user_id = str(get_config()["configurable"]["langgraph_auth_user_id"])
        return ensure_sandbox_id(user_id)

    def _get_sandbox(self) -> Sandbox:
        sandbox = self._sandboxes.get(self.id)
        if sandbox is not None:
            return sandbox
        sandbox = _connect_sandbox(self.id)
        with self._lock:
            return self._sandboxes.setdefault(self.id, sandbox)

    def _drop_sandbox(self) -> None:
        with self._lock:
            self._sandboxes.pop(self.id, None)

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
