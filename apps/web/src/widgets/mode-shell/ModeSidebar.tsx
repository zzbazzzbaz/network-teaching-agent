import {
  BookOpen,
  ChevronsUpDown,
  FlaskConical,
  Folder,
  Layers,
  LogOut,
  MoreHorizontal,
  Pencil,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Terminal,
  Trash2,
} from "lucide-react"
import { useState } from "react"
import { useNavigate, useRouterState, useSearch } from "@tanstack/react-router"
import { toast } from "sonner"

import type { Mode, Session } from "@/shared/api/types"
import { ApiError } from "@/shared/api/client"
import { useAuth } from "@/features/auth"
import {
  MODES,
  useCreateSession,
  useDeleteSession,
  useRenameSession,
  useSessions,
  type PanelId,
} from "@/features/sessions"
import { cn, formatDate, formatTime, relativeDay } from "@/shared/lib/utils"
import { Wordmark } from "@/shared/ui/brand"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/shared/ui/alert-dialog"
import { Button } from "@/shared/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"

const MODE_ICON = { learn: BookOpen, lab: FlaskConical } as const

const UTILITIES: Record<
  Mode,
  { id: PanelId; label: string; icon: typeof Layers }[]
> = {
  learn: [
    { id: "questions", label: "题库", icon: Layers },
    { id: "memory", label: "记忆", icon: Folder },
  ],
  lab: [
    { id: "sandbox", label: "沙盒", icon: Terminal },
    { id: "memory", label: "记忆", icon: Folder },
  ],
}

type SessionSearch = {
  panel?: PanelId
  question?: string
  path?: string
}

function sessionIdFromPath(pathname: string): string | undefined {
  const match = /^\/(?:learn|lab)\/([^/]+)\/?$/.exec(pathname)
  return match?.[1]
}

function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof TypeError) return "无法连接服务器，请确认服务已启动"
  return fallback
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
  const utils = UTILITIES[mode]
  const activePanel = utils.find((item) => item.id === rawSearch.panel)?.id

  const sessionsQuery = useSessions(MODES[mode].agentId)
  const sessions = sessionsQuery.data?.pages.flatMap((page) => page.items) ?? []
  const total = sessionsQuery.data?.pages[0]?.total ?? 0

  const create = useCreateSession(mode)
  const rename = useRenameSession()
  const remove = useDeleteSession()

  const [renaming, setRenaming] = useState<Session | null>(null)
  const [deleting, setDeleting] = useState<Session | null>(null)
  const [draftTitle, setDraftTitle] = useState("")

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

  async function handleNewSession() {
    if (create.isPending) return
    try {
      const created = await create.mutateAsync()
      goToSession(created.session_id)
    } catch (error) {
      toast.error(errorText(error, "创建会话失败"))
    }
  }

  function openPanel(panel: PanelId | null) {
    if (!sessionId) return
    const next: SessionSearch = {}
    if (panel) {
      next.panel = panel
      if (panel === "memory" && rawSearch.path) next.path = rawSearch.path
    }
    goToSession(sessionId, next)
  }

  async function saveRename() {
    if (!renaming) return
    const title = draftTitle.trim() || "新会话"
    if (title === renaming.title) {
      setRenaming(null)
      return
    }
    try {
      await rename.mutateAsync({ sessionId: renaming.session_id, title })
      setRenaming(null)
      toast("会话已重命名")
    } catch (error) {
      toast.error(errorText(error, "重命名失败"))
    }
  }

  async function confirmDelete() {
    if (!deleting) return
    const target = deleting
    const wasCurrent = target.session_id === sessionId
    try {
      await remove.mutateAsync(target)
      setDeleting(null)
      toast("会话已删除")
      if (wasCurrent) {
        const next = sessions.find(
          (item) => item.session_id !== target.session_id,
        )
        if (next) goToSession(next.session_id)
        else goToModeHome()
      }
    } catch (error) {
      toast.error(errorText(error, "删除会话失败"))
    }
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
        {sessionId ? (
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
        ) : null}

        <button
          type="button"
          onClick={() => void handleNewSession()}
          disabled={create.isPending}
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
          {!collapsed && (create.isPending ? "创建中…" : "新建会话")}
        </button>
      </div>

      {collapsed ? (
        <div className="min-h-0 flex-1" />
      ) : (
        <div className="mt-4 flex min-h-0 flex-1 flex-col border-t border-line px-3 pt-3">
          <div className="flex items-baseline justify-between px-1 pb-1">
            <span className="text-[10.5px] font-medium text-ink-muted">会话</span>
            <span className="font-mono text-[9.5px] text-ink-muted">
              {total}
            </span>
          </div>

          <nav
            aria-label="会话列表"
            className="scroll-slim -mx-1 min-h-0 flex-1 overflow-y-auto px-1 pb-2"
          >
            {sessionsQuery.isLoading ? (
              <div className="space-y-2 px-1 py-2" aria-label="会话加载中">
                {[0, 1, 2].map((index) => (
                  <div
                    key={index}
                    className="h-[54px] animate-pulse rounded-md bg-surface-3"
                  />
                ))}
              </div>
            ) : sessionsQuery.isError ? (
              <div className="px-2 py-8 text-center">
                <p className="text-[12px] text-ink-muted">会话加载失败</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => void sessionsQuery.refetch()}
                >
                  重试
                </Button>
              </div>
            ) : sessions.length === 0 ? (
              <div className="px-2 py-8 text-center">
                <p className="text-[12px] text-ink-muted">还没有会话</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => void handleNewSession()}
                >
                  新建第一个会话
                </Button>
              </div>
            ) : (
              <>
                <ul className="space-y-1">
                  {sessions.map((session) => {
                    const active = session.session_id === sessionId
                    return (
                      <li key={session.session_id} className="group/item relative">
                        <button
                          type="button"
                          onClick={() => goToSession(session.session_id)}
                          aria-current={active ? "page" : undefined}
                          className={cn(
                            "block w-full rounded-md border py-2 pr-2.5 pl-3 text-left transition-colors",
                            active
                              ? "border-line bg-surface"
                              : "border-transparent hover:bg-surface/70",
                          )}
                        >
                          {active && (
                            <span
                              aria-hidden="true"
                              className="absolute top-2.5 bottom-2.5 left-0 w-[2px] rounded-full bg-link"
                            />
                          )}
                          <span className="flex items-baseline gap-2">
                            <span
                              className={cn(
                                "min-w-0 flex-1 truncate pr-9 text-[12.5px] leading-5",
                                active ? "font-medium text-ink" : "text-ink-soft",
                              )}
                            >
                              {session.title || "新会话"}
                            </span>
                          </span>
                          <span className="mt-0.5 flex items-center gap-2">
                            <span className="min-w-0 flex-1 truncate text-[10.5px] leading-4 text-ink-muted">
                              最后活跃
                            </span>
                            <time
                              dateTime={session.updated_at}
                              className="shrink-0 text-[9.5px] tabular-nums text-ink-muted"
                            >
                              {relativeDay(session.updated_at) === "今天"
                                ? formatTime(session.updated_at)
                                : formatDate(session.updated_at)}
                            </time>
                          </span>
                        </button>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button
                              type="button"
                              aria-label={`管理会话「${session.title || "新会话"}」`}
                              className="absolute top-1.5 right-1 flex size-7 items-center justify-center rounded-sm text-ink-muted opacity-100 transition-opacity hover:bg-surface-3 hover:text-ink focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring/30 lg:opacity-0 lg:group-hover/item:opacity-100"
                            >
                              <MoreHorizontal
                                className="size-3.5"
                                aria-hidden="true"
                              />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="start" className="w-36">
                            <DropdownMenuItem
                              onSelect={() => {
                                setRenaming(session)
                                setDraftTitle(session.title || "新会话")
                              }}
                            >
                              <Pencil className="size-3.5" aria-hidden="true" />
                              重命名
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              variant="destructive"
                              onSelect={() => setDeleting(session)}
                            >
                              <Trash2 className="size-3.5" aria-hidden="true" />
                              删除会话
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </li>
                    )
                  })}
                </ul>
                {sessionsQuery.hasNextPage && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 w-full text-[11.5px]"
                    disabled={sessionsQuery.isFetchingNextPage}
                    onClick={() => void sessionsQuery.fetchNextPage()}
                  >
                    {sessionsQuery.isFetchingNextPage ? "加载中…" : "加载更多"}
                  </Button>
                )}
              </>
            )}
          </nav>
        </div>
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
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12.5px] font-medium text-ink">
                      {displayName}
                    </span>
                    <span className="block truncate text-[10px] text-ink-muted">
                      学生账号
                    </span>
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

      <Dialog
        open={Boolean(renaming)}
        onOpenChange={(open) => {
          if (!open) setRenaming(null)
        }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>重命名会话</DialogTitle>
            <DialogDescription className="sr-only">
              修改这个会话在侧栏里的标题。
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              void saveRename()
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="session-title">会话标题</Label>
              <Input
                id="session-title"
                name="session-title"
                value={draftTitle}
                onChange={(event) => setDraftTitle(event.target.value)}
                maxLength={100}
                autoComplete="off"
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setRenaming(null)}
              >
                取消
              </Button>
              <Button type="submit" disabled={rename.isPending}>
                {rename.isPending ? "保存中…" : "保存"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => {
          if (!open) setDeleting(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除这个会话？</AlertDialogTitle>
            <AlertDialogDescription>
              「{deleting?.title || "新会话"}」的对话记录会被删除。题库中的题目和沙盒里的文件不受影响。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault()
                void confirmDelete()
              }}
              disabled={remove.isPending}
            >
              {remove.isPending ? "删除中…" : "删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
