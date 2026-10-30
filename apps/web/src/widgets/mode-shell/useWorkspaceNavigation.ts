import { useCallback } from "react"
import { useNavigate } from "@tanstack/react-router"

import type { Mode } from "@/shared/api/types"
import type { SessionSearch } from "@/features/sessions"

/**
 * 会话页和草稿面板页共用的 URL 导航。
 * search 的所有变更都从这里走，避免两套 selectQuestion/selectMemoryPath 漂移。
 */
export function useWorkspaceNavigation({
  mode,
  sessionId,
  search,
}: {
  mode: Mode
  sessionId?: string
  search: SessionSearch
}) {
  const navigate = useNavigate()

  const updateSearch = useCallback(
    (next: SessionSearch, replace = false) => {
      if (sessionId) {
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
        return
      }

      if (mode === "learn") {
        void navigate({ to: "/learn", search: next, replace })
      } else {
        void navigate({ to: "/lab", search: next, replace })
      }
    },
    [mode, navigate, sessionId],
  )

  const closePanel = useCallback(() => {
    updateSearch({})
  }, [updateSearch])

  const selectQuestion = useCallback(
    (questionId: string | undefined) => {
      updateSearch({
        panel: "questions",
        kp: search.kp,
        question: questionId,
      })
    },
    [search.kp, updateSearch],
  )

  const selectKnowledgePoint = useCallback(
    (
      knowledgePointId: string | undefined,
      options?: { replace?: boolean },
    ) => {
      updateSearch(
        knowledgePointId
          ? { panel: "questions", kp: knowledgePointId }
          : { panel: "questions" },
        options?.replace,
      )
    },
    [updateSearch],
  )

  const selectMemoryPath = useCallback(
    (
      path: string | undefined,
      options?: { replace?: boolean },
    ) => {
      updateSearch(
        path ? { panel: "memory", path } : { panel: "memory" },
        options?.replace,
      )
    },
    [updateSearch],
  )

  return {
    updateSearch,
    closePanel,
    selectQuestion,
    selectKnowledgePoint,
    selectMemoryPath,
  }
}
