/** 浏览器端登录态存储：access + refresh + 用户信息。 */

export interface AuthSession {
  userId: string;
  username: string;
  accessToken: string;
  refreshToken: string;
}

const STORAGE_KEY = "computer-network-agent.auth";

let cached: AuthSession | null | undefined;

function readStorage(): AuthSession | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (!parsed.accessToken || !parsed.refreshToken || !parsed.userId || !parsed.username) {
      return null;
    }
    return {
      userId: parsed.userId,
      username: parsed.username,
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
    };
  } catch {
    return null;
  }
}

export function getSession(): AuthSession | null {
  if (cached === undefined) {
    cached = readStorage();
  }
  return cached;
}

export function setSession(session: AuthSession): void {
  cached = session;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // 存储不可用时仅保留内存态
  }
}

export function clearSession(): void {
  cached = null;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 忽略
  }
}

export function getAccessToken(): string | null {
  return getSession()?.accessToken ?? null;
}
