import { Link, Navigate, useParams, useSearchParams } from "react-router-dom"

import { ChatPane } from "@/components/chat/chat-pane"
import { MemoryPanel } from "@/components/panels/memory-panel"
import { QuestionPanel } from "@/components/panels/question-panel"
import { SandboxPanel } from "@/components/panels/sandbox-panel"
import { Button } from "@/components/ui/button"
import { WorkspaceBar } from "@/layout/WorkspaceBar"
import { MODES, type PanelId } from "@/lib/modes"
import type { Mode } from "@/lib/mock"
import { useStore } from "@/lib/store"

export function SessionPage({ mode }: { mode: Mode }) {
  const { sessionId } = useParams<{ sessionId: string }>()
  const { getSession, messagesFor } = useStore()
  const [params, setParams] = useSearchParams()

  const session = sessionId ? getSession(sessionId) : undefined
  const config = MODES[mode]
  const rawPanel = params.get("panel")
  const panel = config.panels.find((item) => item.id === rawPanel)?.id as
    | PanelId
    | undefined

  function backToChat() {
    const search = new URLSearchParams(params)
    search.delete("panel")
    search.delete("question")
    search.delete("path")
    setParams(search)
  }

  if (!session) {
    return (
      <div className="flex h-dvh flex-col">
        <WorkspaceBar title="会话不存在" />
        <main
          id="main"
          className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 text-center"
        >
          <p className="font-mono text-[11px] text-ink-muted">{sessionId}</p>
          <h1 className="mt-2 text-[18px] font-semibold text-ink">
            找不到这个会话
          </h1>
          <p className="mt-1.5 max-w-[36ch] text-[12.5px] leading-6 text-ink-muted">
            它可能已经被删除，或者链接不完整。
          </p>
          <Button asChild variant="outline" className="mt-5">
            <Link to={config.path}>返回{config.label}工作台</Link>
          </Button>
        </main>
      </div>
    )
  }

  if (session.mode !== mode) {
    return <Navigate to={`/${session.mode}/${session.id}`} replace />
  }

  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar
        title={session.title}
        subtitle={panel ? `${config.label}模式` : `${messagesFor(session.id).length} 条消息`}
        onBack={panel ? backToChat : undefined}
      />

      <main id="main" className="flex min-h-0 flex-1 flex-col">
        <h1 className="sr-only">{session.title}</h1>

        {panel === "questions" ? (
          <QuestionPanel />
        ) : panel === "sandbox" ? (
          <SandboxPanel />
        ) : panel === "memory" ? (
          <MemoryPanel />
        ) : (
          <ChatPane session={session} mode={mode} />
        )}
      </main>
    </div>
  )
}
