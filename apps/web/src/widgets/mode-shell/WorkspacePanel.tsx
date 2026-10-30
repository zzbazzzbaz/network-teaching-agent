import { lazy, Suspense } from "react"

import type { PanelId } from "@/features/sessions"

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

/**
 * 工作区侧面板。题库和记忆是用户级能力，不依赖会话；
 * 会话页和草稿首页共用同一套渲染。
 */
export function WorkspacePanel({
  panel,
  selectedQuestionId,
  selectedKnowledgePointId,
  memoryPath,
  onSelectQuestion,
  onSelectKnowledgePoint,
  onSelectMemoryPath,
}: {
  panel: PanelId
  selectedQuestionId?: string
  selectedKnowledgePointId?: string
  memoryPath?: string
  onSelectQuestion: (id: string | undefined) => void
  onSelectKnowledgePoint: (
    id: string | undefined,
    options?: { replace?: boolean },
  ) => void
  onSelectMemoryPath: (path: string | undefined) => void
}) {
  return (
    <Suspense fallback={<PanelPending />}>
      {panel === "questions" ? (
        <QuestionPanel
          selectedQuestionId={selectedQuestionId}
          selectedKnowledgePointId={selectedKnowledgePointId}
          onSelectQuestion={onSelectQuestion}
          onSelectKnowledgePoint={onSelectKnowledgePoint}
        />
      ) : panel === "sandbox" ? (
        <SandboxPanel />
      ) : panel === "memory" ? (
        <MemoryPanel path={memoryPath} onPathChange={onSelectMemoryPath} />
      ) : null}
    </Suspense>
  )
}
