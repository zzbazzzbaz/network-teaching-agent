import { Navigate, useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { WorkspaceBar } from "@/layout/WorkspaceBar"
import { MODES } from "@/lib/modes"
import type { Mode } from "@/lib/mock"
import { useStore } from "@/lib/store"

export function ModeEntry({ mode }: { mode: Mode }) {
  const navigate = useNavigate()
  const { sessions, createSession } = useStore()
  const config = MODES[mode]

  const latest = sessions
    .filter((session) => session.mode === mode)
    .toSorted((a, b) => +new Date(b.updatedAt) - +new Date(a.updatedAt))[0]

  if (latest) {
    return <Navigate to={`/${mode}/${latest.id}`} replace />
  }

  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar title={config.label} />
      <main
        id="main"
        className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 text-center"
      >
        <h1 className="text-[20px] font-semibold text-ink">
          还没有{config.label}会话
        </h1>
        <p className="mt-2 max-w-[34ch] text-[12.5px] leading-6 text-ink-muted">
          新建一个会话，开始和老师对话。
        </p>
        <Button
          className="mt-5 gap-1.5"
          onClick={() => {
            const session = createSession(mode)
            navigate(`/${mode}/${session.id}`)
          }}
        >
          新建会话
        </Button>
      </main>
    </div>
  )
}
