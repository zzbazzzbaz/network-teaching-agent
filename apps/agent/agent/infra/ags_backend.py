from deepagents.backends.protocol import ExecuteResponse, FileDownloadResponse, FileUploadResponse
from deepagents.backends.sandbox import BaseSandbox
from e2b import (
    CommandExitException,
    CommandResult,
    FileNotFoundException,
    Sandbox,
    SandboxException,
)

DEFAULT_WORK_DIR = "/home/user/workspace"


class AgsBackend(BaseSandbox):
    enable_capture_offload = True

    def __init__(self, *, sandbox: Sandbox, work_dir: str = DEFAULT_WORK_DIR) -> None:
        self._sandbox = sandbox
        self._default_timeout = 3600
        self._user = "user"
        self._work_dir = work_dir

    @property
    def id(self) -> str:
        return self._sandbox.sandbox_id

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        timeout = self._default_timeout if timeout is None else timeout
        try:
            result: CommandResult = self._sandbox.commands.run(
                command,
                cwd=self._work_dir,
                timeout=timeout,
                user=self._user,
            )
        except CommandExitException as e:
            result = e
        except SandboxException as e:
            return ExecuteResponse(
                output=f"{type(e).__name__}: {e}",
                exit_code=None,
            )
        return ExecuteResponse(
            output=_combine(result.stdout, result.stderr),
            exit_code=result.exit_code,
        )

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        responses: list[FileUploadResponse] = []
        for path, data in files:
            try:
                self._sandbox.files.write(path, data, user=self._user)
                responses.append(FileUploadResponse(path=path))
            except SandboxException as e:
                responses.append(FileUploadResponse(path=path, error=_file_error(e)))
        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        responses: list[FileDownloadResponse] = []
        for path in paths:
            try:
                content = self._sandbox.files.read(path, format="bytes", user=self._user)
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
