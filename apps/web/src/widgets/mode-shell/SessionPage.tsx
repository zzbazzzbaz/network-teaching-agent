import { lazy, Suspense, useEffect } from "react"
import { useSearch } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

import type { Mode } from "@/shared/api/types"
import {
  DEFAULT_SESSION_TITLE,
  MODES,
  panelLabel,
  sessionQueryOptions,
  touchSession,
  type SessionSearch,
} from "@/features/sessions"
import { Button } from "@/shared/ui/button"
import { cn } from "@/shared/lib/utils"

import { WorkspaceBar } from "./WorkspaceBar"
import { WorkspacePanel } from "./WorkspacePanel"
import { WorkspacePending } from "./WorkspacePending"
import { useWorkspaceNavigation } from "./useWorkspaceNavigation"

const ChatPane = lazy(() =>
  import("@/features/chat").then((module) => ({ default: module.ChatPane })),
)

export function SessionPage({
  mode,
  sessionId,
}: {
  mode: Mode
  sessionId: string
}) {
  const search = useSearch({ strict: false }) as SessionSearch
  const sessionQuery = useQuery(sessionQueryOptions(sessionId))
  const session = sessionQuery.data

  useEffect(() => {
    void touchSession(sessionId).catch(() => undefined)
  }, [sessionId])

  const {
    closePanel,
    selectQuestion,
    selectKnowledgePoint,
    selectMemoryPath,
  } = useWorkspaceNavigation({ mode, sessionId, search })

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

  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar
        title={
          panelTitle
            ? `${panelTitle} · ${session.title || DEFAULT_SESSION_TITLE}`
            : session.title || DEFAULT_SESSION_TITLE
        }
        onBack={panel ? closePanel : undefined}
      />

      <main id="main" className="flex min-h-0 flex-1 flex-col">
        <h1 className="sr-only">{session.title || DEFAULT_SESSION_TITLE}</h1>

        <Suspense fallback={<WorkspacePending />}>
          {/* 面板打开时保持聊天挂载：流式回答、输入内容和附件预览不被卸载。 */}
          <div
            className={cn(
              "flex min-h-0 flex-1 flex-col",
              panel && "hidden",
            )}
            aria-hidden={panel ? true : undefined}
          >
            <ChatPane
              key={session.session_id}
              session={session}
              mode={mode}
            />
          </div>
        </Suspense>
        {panel ? (
          <Suspense fallback={<WorkspacePending />}>
            <WorkspacePanel
              panel={panel}
              selectedQuestionId={search.question}
              selectedKnowledgePointId={search.kp}
              memoryPath={search.path}
              onSelectQuestion={selectQuestion}
              onSelectKnowledgePoint={selectKnowledgePoint}
              onSelectMemoryPath={selectMemoryPath}
            />
          </Suspense>
        ) : null}
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
