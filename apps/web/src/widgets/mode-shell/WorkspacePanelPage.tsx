import {
  panelLabel,
  type PanelId,
  type SessionSearch,
} from "@/features/sessions"
import type { Mode } from "@/shared/api/types"

import { WorkspaceBar } from "./WorkspaceBar"
import { WorkspacePanel } from "./WorkspacePanel"
import { useWorkspaceNavigation } from "./useWorkspaceNavigation"

/**
 * 没有会话时也能打开的面板页（题库 / 记忆 / 沙盒）。
 * 草稿首页和会话页共用同一套 URL search 语义。
 */
export function WorkspacePanelPage({
  mode,
  panel,
  search,
}: {
  mode: Mode
  panel: PanelId
  search: SessionSearch
}) {
  const title = panelLabel(mode, panel) ?? (mode === "learn" ? "学习" : "实验")
  const {
    closePanel,
    selectQuestion,
    selectKnowledgePoint,
    selectMemoryPath,
  } = useWorkspaceNavigation({ mode, search })

  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar title={title} onBack={closePanel} />
      <main id="main" className="flex min-h-0 flex-1 flex-col">
        <h1 className="sr-only">{title}</h1>
        <WorkspacePanel
          panel={panel}
          selectedQuestionId={search.question}
          selectedKnowledgePointId={search.kp}
          memoryPath={search.path}
          onSelectQuestion={selectQuestion}
          onSelectKnowledgePoint={selectKnowledgePoint}
          onSelectMemoryPath={selectMemoryPath}
        />
      </main>
    </div>
  )
}
