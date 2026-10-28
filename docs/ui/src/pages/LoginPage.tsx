import { Eye, EyeOff } from "lucide-react"
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"

import { LayerMark, Wordmark } from "@/components/brand"
import { LayerDiagram } from "@/components/layer-diagram"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function LoginPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [studentId, setStudentId] = useState("2023010421")
  const [password, setPassword] = useState("netlab2026")

  useEffect(() => {
    const html = document.documentElement
    const body = document.body
    const previousHtmlOverflow = html.style.overflow
    const previousBodyOverflow = body.style.overflow

    html.style.overflow = "hidden"
    body.style.overflow = "hidden"

    const preventWheel = (event: WheelEvent) => {
      if (event.ctrlKey) return
      event.preventDefault()
    }
    window.addEventListener("wheel", preventWheel, { passive: false })

    return () => {
      html.style.overflow = previousHtmlOverflow
      body.style.overflow = previousBodyOverflow
      window.removeEventListener("wheel", preventWheel)
    }
  }, [])

  return (
    <div className="h-dvh overflow-hidden overscroll-none bg-surface">
      <div className="grid h-full lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <aside className="relative hidden flex-col overflow-hidden bg-ink px-12 py-10 lg:flex xl:px-16">
          <LayerMark className="pointer-events-none absolute -right-16 -bottom-16 size-80 text-white/[0.05]" />

          <div className="relative">
            <Wordmark tone="dark" />
          </div>

          <LayerDiagram
            tone="dark"
            className="relative my-auto max-w-[360px] opacity-80"
          />
        </aside>

        <main
          id="main"
          className="flex h-full min-h-0 flex-col justify-center overflow-hidden px-6 py-6 lg:px-12 lg:py-10 xl:px-16"
        >
          <div className="mx-auto w-full max-w-[342px]">
            <Wordmark className="mb-10 lg:hidden" />

            <h1 className="text-[26px] leading-tight font-semibold tracking-[-0.015em] text-ink">
              登录课程空间
            </h1>
            <p className="mt-2 text-[13px] leading-6 text-ink-muted">
              使用学号登录，进入课程工作台。
            </p>

            <form
              className="mt-8 space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                navigate("/learn")
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="student-id">学号</Label>
                <Input
                  id="student-id"
                  name="student-id"
                  inputMode="numeric"
                  autoComplete="username"
                  spellCheck={false}
                  value={studentId}
                  onChange={(event) => setStudentId(event.target.value)}
                  placeholder="例如 2023010421"
                  className="h-10 text-[16px] lg:text-[14px]"
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

              <Button type="submit" className="h-10 w-full">
                登录
              </Button>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}
