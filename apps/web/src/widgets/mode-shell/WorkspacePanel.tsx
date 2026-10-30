import { lazy, Suspense } from "react"

import type { PanelId } from "@/features/sessions"

import { WorkspacePending } from "./WorkspacePending"

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
  onSelectMemoryPath: (
    path: string | undefined,
    options?: { replace?: boolean },
  ) => void
}) {
  return (
    <Suspense fallback={<WorkspacePending />}>
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
