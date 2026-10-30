import { apiFetch } from "@/shared/api/client"
import type { AuthResponse } from "@/shared/api/types"

export function login(username: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  })
}


export type { AuthResponse } from "@/shared/api/types"
