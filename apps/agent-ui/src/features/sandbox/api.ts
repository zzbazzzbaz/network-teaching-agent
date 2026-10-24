import { apiFetch } from "@/shared/http";

export interface SandboxInfo {
  sandbox_id: string;
  status: "running";
  vscode_url: string;
  ttyd_url: string;
  expires_at: string;
}

export function getSandbox(): Promise<SandboxInfo> {
  return apiFetch<SandboxInfo>("/sandbox");
}

export function ensureSandbox(): Promise<SandboxInfo> {
  return apiFetch<SandboxInfo>("/sandbox", { method: "POST" });
}

export function stopSandbox(): Promise<void> {
  return apiFetch<void>("/sandbox", { method: "DELETE" });
}
