import { apiFetch } from "@/shared/http";

export type SandboxLifecycleStatus = "running" | "paused" | "stopping";

export interface SandboxInfo {
  sandbox_id: string;
  status: SandboxLifecycleStatus;
  vscode_url: string | null;
  ttyd_url: string | null;
  expires_at: string;
  last_active_at: string;
  paused_at: string | null;
  hard_destroy_at: string;
}

export function getSandbox(): Promise<SandboxInfo> {
  return apiFetch<SandboxInfo>("/sandbox");
}

export function ensureSandbox(): Promise<SandboxInfo> {
  return apiFetch<SandboxInfo>("/sandbox", { method: "POST" });
}

export function heartbeatSandbox(): Promise<SandboxInfo> {
  return apiFetch<SandboxInfo>("/sandbox/heartbeat", { method: "POST" });
}

export function pauseSandbox(): Promise<SandboxInfo> {
  return apiFetch<SandboxInfo>("/sandbox/pause", { method: "POST" });
}

export function stopSandbox(): Promise<void> {
  return apiFetch<void>("/sandbox", { method: "DELETE" });
}
