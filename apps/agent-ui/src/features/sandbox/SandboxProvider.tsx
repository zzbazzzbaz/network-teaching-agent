import * as React from "react";

import { ApiError } from "@/shared/http";

import {
  ensureSandbox,
  getSandbox,
  heartbeatSandbox,
  pauseSandbox,
  stopSandbox,
  type SandboxInfo,
  type SandboxLifecycleStatus,
} from "./api";

export type SandboxStatus =
  | "idle"
  | "starting"
  | "running"
  | "paused"
  | "stopping"
  | "error";

interface SandboxContextValue {
  status: SandboxStatus;
  sandbox: SandboxInfo | null;
  error: string | null;
  ensure: () => Promise<SandboxInfo>;
  pause: () => Promise<void>;
  stop: () => Promise<void>;
}

const SandboxContext = React.createContext<SandboxContextValue | null>(null);

const HEARTBEAT_MS = 5 * 60 * 1000;

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function toUiStatus(status: SandboxLifecycleStatus): SandboxStatus {
  return status;
}

export function SandboxProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<SandboxStatus>("idle");
  const [sandbox, setSandbox] = React.useState<SandboxInfo | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const inFlight = React.useRef<Promise<SandboxInfo> | null>(null);
  const requestSeq = React.useRef(0);

  const refresh = React.useCallback(async () => {
    const seq = ++requestSeq.current;
    setError(null);
    try {
      const info = await getSandbox();
      if (seq !== requestSeq.current) return;
      setSandbox(info);
      setStatus(toUiStatus(info.status));
    } catch (err) {
      if (seq !== requestSeq.current) return;
      if (err instanceof ApiError && err.status === 404) {
        setSandbox(null);
        setStatus("idle");
        return;
      }
      setError(errorMessage(err));
      setStatus("error");
    }
  }, []);

  React.useEffect(() => {
    // 首次进入页面时查询账户沙箱，不主动创建。
    // oxlint-disable-next-line react/set-state-in-effect
    void refresh();
  }, [refresh]);

  React.useEffect(() => {
    if (status !== "running") return;

    const timer = window.setInterval(() => {
      const seq = requestSeq.current;
      void heartbeatSandbox()
        .then((info) => {
          if (seq !== requestSeq.current) return;
          setSandbox(info);
          setStatus(toUiStatus(info.status));
        })
        .catch((err: unknown) => {
          if (seq !== requestSeq.current) return;
          if (!(err instanceof ApiError)) return;
          if (err.status === 404) {
            setSandbox(null);
            setStatus("idle");
          } else if (err.status === 409) {
            setStatus("stopping");
          }
        });
    }, HEARTBEAT_MS);

    return () => window.clearInterval(timer);
  }, [status]);

  React.useEffect(() => {
    if (status !== "stopping") return;

    const timer = window.setInterval(() => {
      void refresh();
    }, 10_000);

    return () => window.clearInterval(timer);
  }, [status, refresh]);

  const ensure = React.useCallback(async () => {
    if (inFlight.current) return inFlight.current;

    const seq = ++requestSeq.current;
    setStatus("starting");
    setError(null);
    const promise = ensureSandbox()
      .then((info) => {
        if (seq === requestSeq.current) {
          setSandbox(info);
          setStatus(toUiStatus(info.status));
        }
        return info;
      })
      .catch((err: unknown) => {
        if (seq === requestSeq.current) {
          setError(errorMessage(err));
          setStatus(
            err instanceof ApiError && err.status === 409 ? "stopping" : "error",
          );
        }
        throw err;
      })
      .finally(() => {
        inFlight.current = null;
      });
    inFlight.current = promise;
    return promise;
  }, []);

  const pause = React.useCallback(async () => {
    const seq = ++requestSeq.current;
    setError(null);
    try {
      const info = await pauseSandbox();
      if (seq !== requestSeq.current) return;
      setSandbox(info);
      setStatus(toUiStatus(info.status));
    } catch (err) {
      if (seq !== requestSeq.current) return;
      setError(errorMessage(err));
      setStatus(err instanceof ApiError && err.status === 409 ? "stopping" : "error");
    }
  }, []);

  const stop = React.useCallback(async () => {
    const seq = ++requestSeq.current;
    setStatus("stopping");
    setError(null);
    try {
      await stopSandbox();
      if (seq !== requestSeq.current) return;
      await refresh();
    } catch (err) {
      if (seq !== requestSeq.current) return;
      setError(errorMessage(err));
      setStatus(err instanceof ApiError && err.status === 503 ? "stopping" : "error");
    }
  }, [refresh]);

  const value = React.useMemo(
    () => ({ status, sandbox, error, ensure, pause, stop }),
    [status, sandbox, error, ensure, pause, stop],
  );

  return <SandboxContext.Provider value={value}>{children}</SandboxContext.Provider>;
}

export function useSandbox(): SandboxContextValue {
  const context = React.useContext(SandboxContext);
  if (context === null) {
    throw new Error("useSandbox 必须在 SandboxProvider 内使用");
  }
  return context;
}
