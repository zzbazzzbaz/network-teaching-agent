import { lazy, Suspense, useEffect, useRef } from "react"
import { useNavigate, useSearch } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

import type { Mode } from "@/shared/api/types"
import {
  MODES,
  panelLabel,
  sessionQueryOptions,
  touchSession,
  useRenameSession,
} from "@/features/sessions"
import { Button } from "@/shared/ui/button"
import { cn } from "@/shared/lib/utils"

import { WorkspaceBar } from "./WorkspaceBar"

const ChatPane = lazy(() =>
  import("@/features/chat").then((module) => ({ default: module.ChatPane })),
)
const QuestionPanel = lazy(() =>
  import("@/features/questions").then((module) => ({
    default: module.QuestionPanel,
  })),
)
const MemoryPanel = lazy(() =>
  import("@/features/memory").then((module) => ({
    default: module.MemoryPanel,
  })),
)
const SandboxPanel = lazy(() =>
  import("@/features/sandbox").then((module) => ({
    default: module.SandboxPanel,
  })),
)

function PanelPending() {
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center bg-surface">
      <span className="size-5 animate-spin rounded-full border-2 border-line-strong border-t-link" />
    </div>
  )
}

export type SessionSearch = {
  panel?: "questions" | "memory" | "sandbox"
  question?: string
  path?: string
}

export function SessionPage({
  mode,
  sessionId,
}: {
  mode: Mode
  sessionId: string
}) {
  const navigate = useNavigate()
  const search = useSearch({ strict: false }) as SessionSearch
  const sessionQuery = useQuery(sessionQueryOptions(sessionId))
  const session = sessionQuery.data
  const rename = useRenameSession()
  const autoTitleDone = useRef(false)

  useEffect(() => {
    autoTitleDone.current = false
    void touchSession(sessionId).catch(() => undefined)
  }, [sessionId])

  function handleUserMessage(text: string) {
    if (!session || autoTitleDone.current) return
    autoTitleDone.current = true
    if (session.title && session.title !== "新会话") return
    const title = text.replace(/\s+/g, " ").trim().slice(0, 30)
    if (title.length < 4) return
    rename.mutate({ sessionId, title })
  }

  if (!session) {
    return (
      <div className="flex h-dvh flex-col">
        <WorkspaceBar title="会话" />
        <main
          id="main"
          className="flex min-h-0 flex-1 items-center justify-center px-6"
        >
          <p className="text-[12.5px] text-ink-muted">正在加载会话…</p>
        </main>
      </div>
    )
  }

  const allowedPanels = MODES[mode].panels
  const panel = allowedPanels.find((item) => item.id === search.panel)?.id
  const panelTitle = panelLabel(mode, panel)

  function updateSearch(next: SessionSearch, replace = false) {
    if (mode === "learn") {
      void navigate({
        to: "/learn/$sessionId",
        params: { sessionId },
        search: next,
        replace,
      })
    } else {
      void navigate({
        to: "/lab/$sessionId",
        params: { sessionId },
        search: next,
        replace,
      })
    }
  }

  function closePanel() {
    updateSearch({})
  }

  function selectQuestion(questionId: string | undefined) {
    if (!questionId) {
      updateSearch({ panel: "questions" })
      return
    }
    updateSearch({ panel: "questions", question: questionId })
  }

  function selectMemoryPath(path: string | undefined) {
    updateSearch(path ? { panel: "memory", path } : { panel: "memory" })
  }

  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar
        title={panelTitle ? `${panelTitle} · ${session.title || "新会话"}` : session.title || "新会话"}
        subtitle={panelTitle ? `${MODES[mode].label}模式 · ${panelTitle}` : `${MODES[mode].label}模式`}
        onBack={panel ? closePanel : undefined}
      />

      <main id="main" className="flex min-h-0 flex-1 flex-col">
        <h1 className="sr-only">{session.title || "新会话"}</h1>

        <Suspense fallback={<PanelPending />}>
          {panel === "questions" ? (
            <QuestionPanel
              selectedQuestionId={search.question}
              onSelectQuestion={selectQuestion}
            />
          ) : panel === "sandbox" ? (
            <SandboxPanel />
          ) : panel === "memory" ? (
            <MemoryPanel path={search.path} onPathChange={selectMemoryPath} />
          ) : (
            <ChatPane
              key={session.session_id}
              session={session}
              mode={mode}
              onUserMessage={handleUserMessage}
            />
          )}
        </Suspense>
      </main>
    </div>
  )
}

export function SessionError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar title="会话" />
      <main
        id="main"
        className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 text-center"
      >
        <h1 className="text-[18px] font-semibold text-ink">无法打开这个会话</h1>
        <p className="mt-2 max-w-[36ch] text-[12.5px] leading-6 text-ink-muted">
          会话可能已被删除，或者运行时暂时不可用。
        </p>
        <Button variant="outline" className={cn("mt-5")} onClick={onRetry}>
          重试
        </Button>
      </main>
    </div>
  )
}
