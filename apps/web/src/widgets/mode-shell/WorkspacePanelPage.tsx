import { useNavigate } from "@tanstack/react-router"

import { panelLabel, type PanelId } from "@/features/sessions"
import type { Mode } from "@/shared/api/types"

import type { SessionSearch } from "./SessionPage"
import { WorkspaceBar } from "./WorkspaceBar"
import { WorkspacePanel } from "./WorkspacePanel"

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
  const navigate = useNavigate()
  const title = panelLabel(mode, panel) ?? (mode === "learn" ? "学习" : "实验")

  function updateSearch(next: SessionSearch, replace = false) {
    if (mode === "learn") {
      void navigate({ to: "/learn", search: next, replace })
    } else {
      void navigate({ to: "/lab", search: next, replace })
    }
  }

  function selectQuestion(questionId: string | undefined) {
    updateSearch({ panel, kp: search.kp, question: questionId })
  }

  function selectKnowledgePoint(
    knowledgePointId: string | undefined,
    options?: { replace?: boolean },
  ) {
    updateSearch(
      knowledgePointId ? { panel, kp: knowledgePointId } : { panel },
      options?.replace,
    )
  }

  function selectMemoryPath(path: string | undefined) {
    updateSearch(path ? { panel, path } : { panel })
  }

  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar title={title} onBack={() => updateSearch({})} />
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
