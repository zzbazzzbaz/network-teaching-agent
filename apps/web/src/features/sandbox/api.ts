import { apiFetch, apiFetchMaybeJson } from "@/shared/api/client"
import type { Sandbox } from "@/shared/api/types"

export interface SandboxDeleteResult {
  status: "stopping"
}

export function fetchSandbox(): Promise<Sandbox> {
  return apiFetch<Sandbox>("/sandbox")
}

export function ensureSandbox(): Promise<Sandbox> {
  return apiFetch<Sandbox>("/sandbox", { method: "POST" })
}

export function heartbeatSandbox(): Promise<Sandbox> {
  return apiFetch<Sandbox>("/sandbox/heartbeat", { method: "POST" })
}

export function pauseSandbox(): Promise<Sandbox> {
  return apiFetch<Sandbox>("/sandbox/pause", { method: "POST" })
}

export function destroySandbox(): Promise<SandboxDeleteResult | undefined> {
  return apiFetchMaybeJson<SandboxDeleteResult>("/sandbox", {
    method: "DELETE",
  })
}
