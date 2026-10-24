import { useSandbox } from "./SandboxProvider";

export function SandboxBar() {
  const { status, sandbox, error, ensure, stop } = useSandbox();

  return (
    <div className="sandbox-bar" data-testid="sandbox-bar">
      <span className="sandbox-label">沙箱</span>

      {status === "idle" && (
        <button
          type="button"
          className="sandbox-action"
          data-testid="sandbox-start"
          onClick={() => void ensure().catch(() => undefined)}
        >
          启动
        </button>
      )}

      {status === "starting" && <span className="sandbox-muted">启动中…</span>}
      {status === "stopping" && <span className="sandbox-muted">停止中…</span>}

      {status === "running" && sandbox && (
        <>
          <a
            className="sandbox-link"
            href={sandbox.vscode_url}
            target="_blank"
            rel="noreferrer"
            data-testid="sandbox-vscode"
          >
            VSCode
          </a>
          <a
            className="sandbox-link"
            href={sandbox.ttyd_url}
            target="_blank"
            rel="noreferrer"
            data-testid="sandbox-ttyd"
          >
            终端
          </a>
          <button
            type="button"
            className="sandbox-action"
            data-testid="sandbox-stop"
            onClick={() => void stop()}
          >
            停止
          </button>
        </>
      )}

      {status === "error" && (
        <>
          <span className="sandbox-error" title={error ?? undefined}>
            {error ?? "沙箱异常"}
          </span>
          <button
            type="button"
            className="sandbox-action"
            data-testid="sandbox-retry"
            onClick={() => void ensure().catch(() => undefined)}
          >
            重试
          </button>
        </>
      )}
    </div>
  );
}
