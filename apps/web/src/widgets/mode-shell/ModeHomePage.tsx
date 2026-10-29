import { useEffect } from "react"
import { useNavigate } from "@tanstack/react-router"
import { toast } from "sonner"

import type { Mode } from "@/shared/api/types"
import { Button } from "@/shared/ui/button"
import { MODES, useCreateSession, useSessions } from "@/features/sessions"

import { WorkspaceBar } from "./WorkspaceBar"

export function ModeHomePage({ mode }: { mode: Mode }) {
  const navigate = useNavigate()
  const sessions = useSessions(MODES[mode].agentId)
  const create = useCreateSession(mode)
  const latest = sessions.data?.pages[0]?.items[0]

  useEffect(() => {
    if (!latest) return
    if (mode === "learn") {
      void navigate({
        to: "/learn/$sessionId",
        params: { sessionId: latest.session_id },
        replace: true,
      })
    } else {
      void navigate({
        to: "/lab/$sessionId",
        params: { sessionId: latest.session_id },
        replace: true,
      })
    }
  }, [latest, mode, navigate])

  async function handleCreate() {
    try {
      const session = await create.mutateAsync()
      if (mode === "learn") {
        void navigate({
          to: "/learn/$sessionId",
          params: { sessionId: session.session_id },
        })
      } else {
        void navigate({
          to: "/lab/$sessionId",
          params: { sessionId: session.session_id },
        })
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建会话失败")
    }
  }

  return (
    <div className="flex h-dvh flex-col">
      <WorkspaceBar title={MODES[mode].label} />
      <main
        id="main"
        className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 text-center"
      >
        {sessions.isLoading || latest ? (
          <div className="flex flex-col items-center gap-3" aria-label="加载中">
            <span className="size-5 animate-spin rounded-full border-2 border-line-strong border-t-link" />
            <p className="text-[12px] text-ink-muted">正在打开最近的会话…</p>
          </div>
        ) : sessions.isError ? (
          <>
            <h1 className="text-[20px] font-semibold text-ink">会话加载失败</h1>
            <p className="mt-2 max-w-[34ch] text-[12.5px] leading-6 text-ink-muted">
              {sessions.error instanceof Error
                ? sessions.error.message
                : "请稍后重试。"}
            </p>
            <Button
              variant="outline"
              className="mt-5"
              onClick={() => void sessions.refetch()}
            >
              重试
            </Button>
          </>
        ) : (
          <>
            <h1 className="text-[20px] font-semibold text-ink">
              还没有{MODES[mode].label}会话
            </h1>
            <p className="mt-2 max-w-[34ch] text-[12.5px] leading-6 text-ink-muted">
              新建一个会话，开始和老师对话。
            </p>
            <Button
              className="mt-5"
              onClick={() => void handleCreate()}
              disabled={create.isPending}
            >
              {create.isPending ? "创建中…" : "新建会话"}
            </Button>
          </>
        )}
      </main>
    </div>
  )
}
