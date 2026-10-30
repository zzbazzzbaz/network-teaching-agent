import {
  BookOpen,
  ChevronsUpDown,
  FlaskConical,
  Folder,
  Layers,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Terminal,
} from "lucide-react"
import { useState } from "react"
import { useNavigate, useRouterState, useSearch } from "@tanstack/react-router"

import type { Mode, Session } from "@/shared/api/types"
import { useAuth } from "@/features/auth"
import {
  MODES,
  useSessions,
  type PanelId,
  type SessionSearch,
} from "@/features/sessions"
import {
  DeleteSessionDialog,
  RenameSessionDialog,
} from "@/features/sessions/ui"
import { cn } from "@/shared/lib/utils"
import { Wordmark } from "@/shared/ui/brand"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu"

import { ModeSessionList } from "./ModeSessionList"
const MODE_ICON = { learn: BookOpen, lab: FlaskConical } as const

const PANEL_ICONS: Record<PanelId, typeof Layers> = {
  questions: Layers,
  memory: Folder,
  sandbox: Terminal,
}

function sessionIdFromPath(pathname: string): string | undefined {
  const match = /^\/(?:learn|lab)\/([^/]+)\/?$/.exec(pathname)
  return match?.[1]
}

export function ModeSidebar({
  mode,
  collapsed = false,
  onToggleCollapse,
  onNavigate,
}: {
  mode: Mode
  collapsed?: boolean
  onToggleCollapse?: () => void
  onNavigate?: () => void
}) {
  const { session: authSession, logout } = useAuth()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (state) => state.location.pathname })
  const rawSearch = useSearch({ strict: false }) as SessionSearch
  const sessionId = sessionIdFromPath(pathname)
  const utils = MODES[mode].panels.map((item) => ({
    ...item,
    icon: PANEL_ICONS[item.id],
  }))
  const activePanel = utils.find((item) => item.id === rawSearch.panel)?.id

  const sessionsQuery = useSessions(MODES[mode].agentId)
  const sessions = sessionsQuery.data?.pages.flatMap((page) => page.items) ?? []
  const total = sessionsQuery.data?.pages[0]?.total ?? 0

  const [renaming, setRenaming] = useState<Session | null>(null)
  const [deleting, setDeleting] = useState<Session | null>(null)

  function goToSession(id: string, search: SessionSearch = {}) {
    onNavigate?.()
    if (mode === "learn") {
      void navigate({
        to: "/learn/$sessionId",
        params: { sessionId: id },
        search,
      })
    } else {
      void navigate({
        to: "/lab/$sessionId",
        params: { sessionId: id },
        search,
      })
    }
  }

  function goToModeHome() {
    onNavigate?.()
    void navigate({ to: MODES[mode].path })
  }

  function goToOtherMode(next: Mode) {
    onNavigate?.()
    void navigate({ to: MODES[next].path })
  }

  function handleNewSession() {
    onNavigate?.()
    if (mode === "learn") {
      void navigate({ to: "/learn", search: {} })
    } else {
      void navigate({ to: "/lab", search: {} })
    }
  }

  function openPanel(panel: PanelId | null) {
    const next: SessionSearch = {}
    if (panel) {
      next.panel = panel
      if (panel === "memory" && rawSearch.path) next.path = rawSearch.path
    }
    if (sessionId) {
      goToSession(sessionId, next)
      return
    }
    onNavigate?.()
    if (mode === "learn") {
      void navigate({ to: "/learn", search: next })
    } else {
      void navigate({ to: "/lab", search: next })
    }
  }

  function handleDeleted(target: Session) {
    if (target.session_id !== sessionId) return
    const next = sessions.find(
      (item) => item.session_id !== target.session_id,
    )
    if (next) goToSession(next.session_id)
    else goToModeHome()
  }

  const brandTo = MODES[mode].path
  const displayName = authSession?.username ?? "学生"

  return (
    <div className="flex h-full min-h-0 flex-col bg-paper">
      <div
        className={cn(
          "flex items-center",
          collapsed ? "justify-center px-2 pt-4 pb-3" : "px-4 pt-4 pb-4",
        )}
      >
        {collapsed ? (
          <Wordmark compact to={brandTo} onClick={onNavigate} />
        ) : (
          <Wordmark to={brandTo} onClick={onNavigate} />
        )}
      </div>

      <div className={cn(collapsed ? "px-2" : "px-3")}>
        <div
          role="group"
          aria-label="切换模式"
          className={cn(
            collapsed
              ? "flex flex-col gap-1"
              : "grid grid-cols-2 gap-0.5 rounded-md bg-surface-3 p-0.5",
          )}
        >
          {(["learn", "lab"] as const).map((item) => {
            const config = MODES[item]
            const Icon = MODE_ICON[item]
            const active = mode === item
            return (
              <button
                key={item}
                type="button"
                onClick={() => (active ? goToModeHome() : goToOtherMode(item))}
                aria-current={active ? "page" : undefined}
                aria-label={config.label}
                title={config.label}
                className={cn(
                  "flex items-center justify-center gap-1.5 rounded-sm border font-medium transition-colors",
                  collapsed ? "h-9 w-full" : "h-8 text-[12.5px]",
                  active
                    ? "border-line bg-surface text-ink"
                    : "border-transparent text-ink-muted hover:text-ink",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {!collapsed && config.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className={cn("mt-4", collapsed ? "px-2" : "px-3")}>
        <nav
          aria-label="功能"
          className={cn(collapsed ? "space-y-1" : "space-y-0.5")}
        >
          {utils.map((item) => {
            const active = activePanel === item.id
            const Icon = item.icon
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => openPanel(active ? null : item.id)}
                aria-current={active ? "page" : undefined}
                aria-label={item.label}
                title={active ? `关闭${item.label}` : `打开${item.label}`}
                className={cn(
                  "flex w-full items-center rounded-md text-left transition-colors",
                  collapsed
                    ? "mx-auto size-10 justify-center"
                    : "h-9 gap-2.5 px-2.5 text-[13px]",
                  active
                    ? "bg-link-soft font-medium text-link-strong"
                    : "text-ink-soft hover:bg-surface hover:text-ink",
                )}
              >
                <Icon
                  className={cn(
                    "size-4 shrink-0",
                    active ? "text-link" : "text-ink-muted",
                  )}
                  aria-hidden="true"
                />
                {!collapsed && <span className="flex-1">{item.label}</span>}
              </button>
            )
          })}
        </nav>

        <button
          type="button"
          onClick={handleNewSession}
          aria-label="新建会话"
          title="新建会话"
          className={cn(
            "flex items-center rounded-md text-left text-ink-soft transition-colors hover:bg-surface hover:text-ink disabled:opacity-50",
            collapsed
              ? "mx-auto mt-1 size-10 justify-center"
              : "mt-0.5 h-9 w-full gap-2.5 px-2.5 text-[13px]",
          )}
        >
          <Plus className="size-4 shrink-0 text-ink-muted" aria-hidden="true" />
          {!collapsed && "新建会话"}
        </button>
      </div>

      {collapsed ? (
        <div className="min-h-0 flex-1" />
      ) : (
        <ModeSessionList
          sessions={sessions}
          total={total}
          activeSessionId={sessionId}
          isLoading={sessionsQuery.isLoading}
          isError={sessionsQuery.isError}
          hasNextPage={sessionsQuery.hasNextPage}
          isFetchingNextPage={sessionsQuery.isFetchingNextPage}
          onSelect={goToSession}
          onRename={setRenaming}
          onDelete={setDeleting}
          onRetry={() => void sessionsQuery.refetch()}
          onLoadMore={() => void sessionsQuery.fetchNextPage()}
          onNew={handleNewSession}
        />
      )}

      <div className="border-t border-line p-2">
        {onToggleCollapse && (
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label={collapsed ? "展开侧栏" : "收起侧栏"}
            title={collapsed ? "展开侧栏" : "收起侧栏"}
            className={cn(
              "flex items-center rounded-md text-ink-muted transition-colors hover:bg-surface hover:text-ink",
              collapsed
                ? "mx-auto mb-1 size-9 justify-center"
                : "mb-1 h-8 w-full gap-2 px-2 text-[11.5px]",
            )}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" aria-hidden="true" />
            ) : (
              <>
                <PanelLeftClose className="size-3.5" aria-hidden="true" />
                收起侧栏
              </>
            )}
          </button>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              aria-label="账户菜单"
              className={cn(
                "flex w-full items-center rounded-md text-left transition-colors hover:bg-surface focus-visible:ring-2 focus-visible:ring-ring/30",
                collapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2 py-2",
              )}
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-link-line bg-link-soft text-[12px] font-semibold text-link-strong">
                {displayName.slice(0, 1).toUpperCase()}
              </span>
              {!collapsed && (
                <>
                  <span className="min-w-0 flex-1 truncate text-[12.5px] font-medium text-ink">
                    {displayName}
                  </span>
                  <ChevronsUpDown
                    className="size-3.5 text-ink-muted"
                    aria-hidden="true"
                  />
                </>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" side="top" className="w-52">
            <DropdownMenuLabel>{MODES[mode].label}模式</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={logout}>
              <LogOut className="size-3.5" aria-hidden="true" />
              退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <RenameSessionDialog
        session={renaming}
        onClose={() => setRenaming(null)}
      />
      <DeleteSessionDialog
        session={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={handleDeleted}
      />
    </div>
  )
}
