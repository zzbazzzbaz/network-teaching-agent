import * as React from "react";

import { ApiError } from "@/shared/http";

import {
  ensureSandbox,
  getSandbox,
  stopSandbox,
  type SandboxInfo,
} from "./api";

export type SandboxStatus = "idle" | "starting" | "stopping" | "running" | "error";

interface SandboxContextValue {
  status: SandboxStatus;
  sandbox: SandboxInfo | null;
  error: string | null;
  ensure: () => Promise<SandboxInfo>;
  stop: () => Promise<void>;
}

const SandboxContext = React.createContext<SandboxContextValue | null>(null);

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
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
      setStatus("running");
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

  const ensure = React.useCallback(async () => {
    if (inFlight.current) return inFlight.current;

    const seq = ++requestSeq.current;
    setStatus("starting");
    setError(null);
    const promise = ensureSandbox()
      .then((info) => {
        if (seq === requestSeq.current) {
          setSandbox(info);
          setStatus("running");
        }
        return info;
      })
      .catch((err) => {
        if (seq === requestSeq.current) {
          setError(errorMessage(err));
          setStatus("error");
        }
        throw err;
      })
      .finally(() => {
        inFlight.current = null;
      });
    inFlight.current = promise;
    return promise;
  }, []);

  const stop = React.useCallback(async () => {
    const seq = ++requestSeq.current;
    setStatus("stopping");
    setError(null);
    try {
      await stopSandbox();
      if (seq !== requestSeq.current) return;
      setSandbox(null);
      setStatus("idle");
    } catch (err) {
      if (seq !== requestSeq.current) return;
      setError(errorMessage(err));
      setStatus("error");
    }
  }, []);

  const value = React.useMemo(
    () => ({ status, sandbox, error, ensure, stop }),
    [status, sandbox, error, ensure, stop],
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
