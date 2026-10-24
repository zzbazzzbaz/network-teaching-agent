import * as React from "react";

import { ensureFreshToken, onUnauthorized } from "@/shared/http";
import {
  clearSession,
  getSession,
  setSession,
  type AuthSession,
} from "@/shared/session";

import { login as loginApi, type AuthResponse } from "./api";

interface AuthContextValue {
  session: AuthSession | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

function toSession(response: AuthResponse): AuthSession {
  return {
    userId: response.user_id,
    username: response.username,
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
  };
}

function goToLogin(): void {
  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = React.useState<AuthSession | null>(() => getSession());

  React.useEffect(() => {
    const unsubscribe = onUnauthorized(() => {
      setSessionState(null);
      goToLogin();
    });

    let cancelled = false;
    void (async () => {
      if (!getSession()) return;
      await ensureFreshToken();
      if (!cancelled) setSessionState(getSession());
    })();

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  const login = React.useCallback(async (username: string, password: string) => {
    const response = await loginApi(username, password);
    const next = toSession(response);
    setSession(next);
    setSessionState(next);
  }, []);

  const logout = React.useCallback(() => {
    clearSession();
    setSessionState(null);
    goToLogin();
  }, []);

  const value = React.useMemo(
    () => ({ session, login, logout }),
    [session, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth 必须在 AuthProvider 内使用");
  }
  return context;
}
