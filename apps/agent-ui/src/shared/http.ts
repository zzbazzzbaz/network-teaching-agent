/** 统一请求层：Bearer 注入、401 自动续期、错误解析。 */

import {
  clearSession,
  getSession,
  setSession,
  type AuthSession,
} from "./session";

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
  signal?: AbortSignal;
}

type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

function notifyUnauthorized(): void {
  clearSession();
  for (const listener of unauthorizedListeners) listener();
}

interface RefreshResponse {
  user_id: string;
  username: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

const REFRESH_TIMEOUT_MS = 15_000;

let refreshInFlight: Promise<AuthSession | null> | null = null;

function refreshSession(): Promise<AuthSession | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const current = getSession();
      if (!current) return null;

      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), REFRESH_TIMEOUT_MS);
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: current.refreshToken }),
          signal: controller.signal,
        });
        if (!response.ok) return null;
        const data = (await response.json()) as RefreshResponse;
        const next: AuthSession = {
          userId: data.user_id,
          username: data.username,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
        };
        setSession(next);
        return next;
      } catch {
        return null;
      } finally {
        window.clearTimeout(timer);
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

/** 解析 JWT 过期时间（仅本地判断用，不校验签名）。 */
function tokenExpiry(token: string): number | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const payload = JSON.parse(atob(padded)) as { exp?: unknown };
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** 登录态即将过期（或已过期）时主动续期。 */
export async function ensureFreshToken(): Promise<void> {
  const session = getSession();
  if (!session) return;

  const expiry = tokenExpiry(session.accessToken);
  if (expiry !== null && expiry - Date.now() > 60_000) return;

  const renewed = await refreshSession();
  if (!renewed) notifyUnauthorized();
}

/**
 * 带登录态的 fetch：每次请求注入最新 access token；遇到 401 自动续期一次。
 * 供 API 与 LangGraph Server 共用。
 */
export async function authedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const withToken = (token: string | null): RequestInit => {
    const headers = new Headers(init.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return { ...init, headers };
  };

  await ensureFreshToken();
  const session = getSession();
  if (!session) {
    return fetch(input, withToken(null));
  }

  let response = await fetch(input, withToken(session.accessToken));
  if (response.status !== 401) return response;

  const renewed = await refreshSession();
  if (!renewed) {
    notifyUnauthorized();
    throw new ApiError(401, "登录已失效，请重新登录");
  }

  response = await fetch(input, withToken(renewed.accessToken));
  if (response.status === 401) {
    notifyUnauthorized();
    throw new ApiError(401, "登录已失效，请重新登录");
  }
  return response;
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string" && detail) return detail;
    }
  } catch {
    // 非 JSON 响应
  }
  return `请求失败（HTTP ${response.status}）`;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, signal } = options;
  const url = `${API_BASE}${path}`;

  const headers = new Headers();
  if (body !== undefined) headers.set("Content-Type", "application/json");

  const init: RequestInit = {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  };

  const response = auth ? await authedFetch(url, init) : await fetch(url, init);

  if (!response.ok) {
    if (auth && response.status === 401) {
      notifyUnauthorized();
      throw new ApiError(401, "登录已失效，请重新登录");
    }
    throw new ApiError(response.status, await parseErrorDetail(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
