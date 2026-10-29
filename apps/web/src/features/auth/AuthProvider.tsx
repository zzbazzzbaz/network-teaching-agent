import * as React from "react"
import { useQueryClient } from "@tanstack/react-query"

import { onUnauthorized } from "@/shared/api/client"
import {
  clearSession,
  getSession,
  setSession,
  type AuthSession,
} from "@/shared/auth/session"

import { login as loginApi, type AuthResponse } from "./api"

interface AuthContextValue {
  session: AuthSession | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = React.createContext<AuthContextValue | null>(null)

function toSession(response: AuthResponse): AuthSession {
  return {
    userId: response.user_id,
    username: response.username,
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
  }
}

function goToLogin(): void {
  if (window.location.pathname !== "/login") {
    window.location.assign("/login")
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSessionState] = React.useState<AuthSession | null>(() =>
    getSession(),
  )

  React.useEffect(() => {
    return onUnauthorized(() => {
      setSessionState(null)
      queryClient.clear()
      goToLogin()
    })
  }, [queryClient])

  const login = React.useCallback(
    async (username: string, password: string) => {
      const response = await loginApi(username, password)
      const next = toSession(response)
      queryClient.clear()
      setSession(next)
      setSessionState(next)
    },
    [queryClient],
  )

  const logout = React.useCallback(() => {
    clearSession()
    setSessionState(null)
    queryClient.clear()
    goToLogin()
  }, [queryClient])

  const value = React.useMemo(
    () => ({ session, login, logout }),
    [session, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext)
  if (context === null) {
    throw new Error("useAuth 必须在 AuthProvider 内使用")
  }
  return context
}
