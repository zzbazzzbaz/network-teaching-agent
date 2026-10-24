/** 认证接口（登录 / 当前用户）。注册接口不对外提供。 */

import { apiFetch } from "@/shared/http";

export interface AuthResponse {
  user_id: string;
  username: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  user_id: string;
  username: string;
}

export function login(username: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
}

export function me(): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/me");
}
