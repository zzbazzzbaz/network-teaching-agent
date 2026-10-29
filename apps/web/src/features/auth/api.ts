import { apiFetch } from "@/shared/api/client"
import type { AuthResponse, UserResponse } from "@/shared/api/types"

export function login(username: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  })
}

export function me(): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/me")
}

export type { AuthResponse } from "@/shared/api/types"
