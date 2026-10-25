import { useState } from "react";

import { useSandbox } from "./SandboxProvider";

type LinkKind = "vscode" | "ttyd";

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function SandboxBar() {
  const { status, sandbox, error, ensure, pause, stop } = useSandbox();
  const [linkError, setLinkError] = useState<string | null>(null);

  const start = () => {
    setLinkError(null);
    void ensure().catch(() => undefined);
  };

  const open = async (kind: LinkKind) => {
    setLinkError(null);
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setLinkError("浏览器拦截了新标签页，请允许弹窗后重试");
      return;
    }
    popup.opener = null;

    try {
      const info = await ensure();
      const url = kind === "vscode" ? info.vscode_url : info.ttyd_url;
      if (!url) throw new Error("沙箱链接不可用");
      popup.location.replace(url);
    } catch (err) {
      popup.close();
      setLinkError(messageOf(err));
    }
  };

  const destroy = () => {
    if (!window.confirm("销毁后 workspace 会丢失，确定销毁沙箱？")) return;
    void stop();
  };

  return (
    <div
      className="sandbox-bar"
      data-testid="sandbox-bar"
      data-sandbox-id={sandbox?.sandbox_id}
    >
      <span className="sandbox-label">沙箱</span>

      {status === "idle" && (
        <button
          type="button"
          className="sandbox-action"
          data-testid="sandbox-start"
          onClick={start}
        >
          启动
        </button>
      )}

      {status === "starting" && <span className="sandbox-muted">启动中…</span>}
      {status === "stopping" && (
        <>
          <span className="sandbox-muted">销毁中…</span>
          {error && (
            <span className="sandbox-error" title={error}>
              {error}
            </span>
          )}
        </>
      )}

      {status === "running" && sandbox && (
        <>
          <a
            className="sandbox-link"
            href={sandbox.vscode_url ?? undefined}
            target="_blank"
            rel="noreferrer"
            data-testid="sandbox-vscode"
            onClick={(event) => {
              event.preventDefault();
              void open("vscode");
            }}
          >
            VSCode
          </a>
          <a
            className="sandbox-link"
            href={sandbox.ttyd_url ?? undefined}
            target="_blank"
            rel="noreferrer"
            data-testid="sandbox-ttyd"
            onClick={(event) => {
              event.preventDefault();
              void open("ttyd");
            }}
          >
            终端
          </a>
          <button
            type="button"
            className="sandbox-action"
            data-testid="sandbox-pause"
            onClick={() => void pause()}
          >
            暂停
          </button>
          <button
            type="button"
            className="sandbox-action sandbox-action-danger"
            data-testid="sandbox-stop"
            onClick={destroy}
          >
            销毁
          </button>
        </>
      )}

      {status === "paused" && sandbox && (
        <>
          <span className="sandbox-muted">已暂停</span>
          <button
            type="button"
            className="sandbox-action"
            data-testid="sandbox-resume"
            onClick={start}
          >
            恢复
          </button>
          <button
            type="button"
            className="sandbox-action sandbox-action-danger"
            data-testid="sandbox-stop"
            onClick={destroy}
          >
            销毁
          </button>
        </>
      )}

      {status === "error" && (
        <>
          <span className="sandbox-error" title={error ?? undefined}>
            {linkError ?? error ?? "沙箱异常"}
          </span>
          <button
            type="button"
            className="sandbox-action"
            data-testid="sandbox-retry"
            onClick={start}
          >
            重试
          </button>
        </>
      )}

      {status === "running" && linkError && (
        <span className="sandbox-error" title={linkError}>
          {linkError}
        </span>
      )}
    </div>
  );
}
