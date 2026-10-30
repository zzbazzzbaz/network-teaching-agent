import { Eye, EyeOff, Loader2 } from "lucide-react"
import { useState } from "react"
import { useNavigate, useSearch } from "@tanstack/react-router"

import { LayerMark, Wordmark } from "@/shared/ui/brand"
import { HandshakeDiagram } from "@/shared/ui/handshake-diagram"
import { LayerDiagram } from "@/shared/ui/layer-diagram"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { humanizeApiError } from "@/shared/api/errors"
import { cn } from "@/shared/lib/utils"

import { useAuth } from "./AuthProvider"

function LoginBrand({
  className,
  tone = "default",
}: {
  className?: string
  tone?: "default" | "dark"
}) {
  const dark = tone === "dark"

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <Wordmark tone={tone} to="/login" />
      <span
        aria-hidden="true"
        className={dark ? "h-4 w-px bg-white/20" : "h-4 w-px bg-line"}
      />
      <span
        className={
          dark
            ? "text-[12px] font-medium tracking-[0.06em] whitespace-nowrap text-white/55"
            : "text-[12px] font-medium tracking-[0.06em] whitespace-nowrap text-ink-muted"
        }
      >
        计算机网络教学智能体
      </span>
    </div>
  )
}

function errorMessage(error: unknown): string {
  return humanizeApiError(error, "登录失败，请稍后重试", {
    401: "账号或密码不正确",
  })
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const search = useSearch({ from: "/login" }) as { redirect?: string }
  const [showPassword, setShowPassword] = useState(false)
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    if (submitting) return
    const name = username.trim()
    if (!name) {
      setError("请输入账号")
      return
    }
    if (!password) {
      setError("请输入密码")
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await login(name, password)
      if (search.redirect) {
        try {
          const url = new URL(search.redirect, window.location.origin)
          if (url.origin === window.location.origin && url.pathname !== "/login") {
            window.location.assign(url.pathname + url.search + url.hash)
            return
          }
        } catch {
          // 非法 redirect，落回工作台
        }
      }
      void navigate({ to: "/learn", replace: true })
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-dvh overflow-x-hidden bg-surface">
      <div className="grid min-h-dvh lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <aside className="relative hidden flex-col overflow-hidden bg-ink px-12 py-10 lg:flex xl:px-16">
          <div
            className="login-grid pointer-events-none absolute inset-0"
            aria-hidden="true"
          />
          <LayerMark className="pointer-events-none absolute -right-16 -bottom-16 size-80 text-white/[0.05]" />

          <div className="relative flex min-h-0 flex-1 flex-col">
            <LoginBrand tone="dark" />

            <div className="login-plate my-auto w-full max-w-[540px]">
              <div className="login-handshake">
                <div className="mb-3 flex items-center gap-2.5">
                  <span
                    aria-hidden="true"
                    className="h-px w-4 bg-white/20"
                  />
                  <span className="font-mono text-[10px] tracking-[0.1em] text-white/40">
                    TCP 三次握手
                  </span>
                </div>
                <HandshakeDiagram tone="dark" />
                <div className="mt-7 border-t border-white/10" />
              </div>

              <div className="pt-5">
                <LayerDiagram tone="dark" />
              </div>
            </div>
          </div>
        </aside>

        <main
          id="main"
          className="flex min-h-dvh flex-col justify-center px-6 py-6 lg:px-12 lg:py-10 xl:px-16"
        >
          <div className="mx-auto w-full max-w-[342px]">
            <LoginBrand className="mb-10 lg:hidden" />

            <h1 className="text-[26px] leading-tight font-semibold tracking-[-0.015em] text-ink">
              登录课程空间
            </h1>
            <p className="mt-2 text-[13px] leading-6 text-ink-muted">
              使用账号登录，进入课程工作台。
            </p>

            <form
              className="mt-8 space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                void submit()
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="student-id">账号</Label>
                <Input
                  id="student-id"
                  name="username"
                  inputMode="text"
                  autoComplete="username"
                  spellCheck={false}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="h-10 text-[16px] lg:text-[14px]"
                  disabled={submitting}
                  autoFocus
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password">密码</Label>
                <div className="relative">
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="输入密码…"
                    className="h-10 pr-10 text-[16px] lg:text-[14px]"
                    disabled={submitting}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    aria-label={showPassword ? "隐藏密码" : "显示密码"}
                    aria-pressed={showPassword}
                    className="absolute top-1/2 right-1 -translate-y-1/2 rounded-sm p-2 text-ink-muted hover:bg-surface-3 hover:text-ink"
                  >
                    {showPassword ? (
                      <EyeOff className="size-4" aria-hidden="true" />
                    ) : (
                      <Eye className="size-4" aria-hidden="true" />
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <p role="alert" className="text-[12px] leading-5 text-danger">
                  {error}
                </p>
              )}

              <Button type="submit" className="h-10 w-full gap-2" disabled={submitting}>
                {submitting && (
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                )}
                {submitting ? "登录中…" : "登录"}
              </Button>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}
