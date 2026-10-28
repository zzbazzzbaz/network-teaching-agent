import {
  BookOpen,
  ChevronsUpDown,
  FlaskConical,
  Folder,
  Layers,
  LogOut,
  MoreHorizontal,
  Palette,
  Pencil,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Terminal,
  Trash2,
} from "lucide-react"
import { useMemo, useState } from "react"
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom"
import { toast } from "sonner"

import { Wordmark } from "@/components/brand"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MODES, type PanelId } from "@/lib/modes"
import { user, type Mode, type Session } from "@/lib/mock"
import { useStore } from "@/lib/store"
import { cn, formatDate, formatTime, relativeDay } from "@/lib/utils"

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

export function Sidebar({
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
  const { sessions, createSession, renameSession, deleteSession } = useStore()
  const navigate = useNavigate()
  const location = useLocation()
  const params = useParams<{ sessionId?: string }>()
  const [searchParams] = useSearchParams()
  const [renaming, setRenaming] = useState<Session | null>(null)
  const [deleting, setDeleting] = useState<Session | null>(null)
  const [draftTitle, setDraftTitle] = useState("")

  const config = MODES[mode]
  const rawPanel = searchParams.get("panel")
  const activePanel = config.panels.find((panel) => panel.id === rawPanel)?.id
  const utilities = UTILITIES[mode]

  const modeSessions = useMemo(
    () =>
      sessions
        .filter((session) => session.mode === mode)
        .toSorted((a, b) => +new Date(b.updatedAt) - +new Date(a.updatedAt)),
    [sessions, mode],
  )

  const brandTo = params.sessionId
    ? `/${mode}/${params.sessionId}`
    : `/${mode}`

  function hrefForPanel(panel: PanelId | null) {
    const next = new URLSearchParams(searchParams)
    next.delete("question")
    next.delete("path")
    if (panel) next.set("panel", panel)
    else next.delete("panel")
    const search = next.toString()
    return {
      pathname: location.pathname,
      search: search ? `?${search}` : "",
    }
  }

  function handleNewSession() {
    const session = createSession(mode)
    onNavigate?.()
    navigate(`/${mode}/${session.id}`)
  }

  function handleLogout() {
    onNavigate?.()
    navigate("/login")
    toast("已退出登录")
  }

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
            const itemConfig = MODES[item]
            const Icon = MODE_ICON[item]
            const active = mode === item
            return (
              <Link
                key={item}
                to={active ? brandTo : `/${item}`}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                aria-label={itemConfig.label}
                title={itemConfig.label}
                className={cn(
                  "flex items-center justify-center gap-1.5 rounded-sm border font-medium transition-colors",
                  collapsed ? "h-9 w-full" : "h-8 text-[12.5px]",
                  active
                    ? "border-line bg-surface text-ink"
                    : "border-transparent text-ink-muted hover:text-ink",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {!collapsed && itemConfig.label}
              </Link>
            )
          })}
        </div>
      </div>

      <div className={cn("mt-4", collapsed ? "px-2" : "px-3")}>
        {params.sessionId ? (
          <nav aria-label="功能" className={cn(collapsed ? "space-y-1" : "space-y-0.5")}>
            {utilities.map((item) => {
              const active = activePanel === item.id
              const Icon = item.icon
              return (
                <Link
                  key={item.id}
                  to={hrefForPanel(active ? null : item.id)}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  aria-label={item.label}
                  title={active ? `关闭${item.label}` : `打开${item.label}`}
                  className={cn(
                    "flex items-center rounded-md transition-colors",
                    collapsed ? "mx-auto size-10 justify-center" : "h-9 gap-2.5 px-2.5 text-[13px]",
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
                </Link>
              )
            })}
          </nav>
        ) : null}

        <button
          type="button"
          onClick={handleNewSession}
          aria-label="新建会话"
          title="新建会话"
          className={cn(
            "flex items-center rounded-md text-left text-ink-soft transition-colors hover:bg-surface hover:text-ink",
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
        <div className="mt-4 flex min-h-0 flex-1 flex-col border-t border-line px-3 pt-3">
          <div className="flex items-baseline justify-between px-1 pb-1">
            <span className="text-[10.5px] font-medium text-ink-muted">会话</span>
            <span className="font-mono text-[9.5px] text-ink-muted">
              {modeSessions.length}
            </span>
          </div>

          <nav
            aria-label="会话列表"
            className="scroll-slim -mx-1 min-h-0 flex-1 overflow-y-auto px-1 pb-2"
          >
            {modeSessions.length === 0 ? (
              <div className="px-2 py-8 text-center">
                <p className="text-[12px] text-ink-muted">还没有会话</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={handleNewSession}
                >
                  新建第一个会话
                </Button>
              </div>
            ) : (
              <ul className="space-y-1">
                {modeSessions.map((session) => {
                  const active = params.sessionId === session.id
                  return (
                    <li key={session.id} className="group/item relative">
                      <Link
                        to={`/${mode}/${session.id}`}
                        onClick={onNavigate}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "block rounded-md border py-2 pr-2.5 pl-3 transition-colors",
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
                              active
                                ? "font-medium text-ink"
                                : "text-ink-soft",
                            )}
                          >
                            {session.title}
                          </span>
                        </span>
                        <span className="mt-0.5 flex items-center gap-2">
                          <span className="line-clamp-1 min-w-0 flex-1 text-[11px] leading-4 text-ink-muted">
                            {session.snippet}
                          </span>
                          <time
                            dateTime={session.updatedAt}
                            className="shrink-0 text-[9.5px] tabular-nums text-ink-muted"
                          >
                            {relativeDay(session.updatedAt) === "今天"
                              ? formatTime(session.updatedAt)
                              : formatDate(session.updatedAt)}
                          </time>
                        </span>
                      </Link>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            type="button"
                            aria-label={`管理会话「${session.title}」`}
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
                              setDraftTitle(session.title)
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
                {user.initials}
              </span>
              {!collapsed && (
                <>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12.5px] font-medium text-ink">
                      {user.name}
                    </span>
                    <span className="block truncate text-[10px] text-ink-muted">
                      {user.studentId}
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
          <DropdownMenuContent align="end" side="top" className="w-56">
            <DropdownMenuLabel>{user.major}</DropdownMenuLabel>
            <DropdownMenuItem asChild>
              <Link to="/styleguide" onClick={onNavigate}>
                <Palette className="size-3.5" aria-hidden="true" />
                设计规范（演示）
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={handleLogout}>
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
              if (!renaming) return
              renameSession(renaming.id, draftTitle)
              setRenaming(null)
              toast("会话已重命名")
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="session-title">会话标题</Label>
              <Input
                id="session-title"
                name="session-title"
                value={draftTitle}
                onChange={(event) => setDraftTitle(event.target.value)}
                maxLength={60}
                autoComplete="off"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRenaming(null)}>
                取消
              </Button>
              <Button type="submit">保存</Button>
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
              「{deleting?.title}」的对话记录会被删除。题库中的题目和沙盒里的文件不受影响。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!deleting) return
                const wasCurrent = params.sessionId === deleting.id
                deleteSession(deleting.id)
                setDeleting(null)
                if (wasCurrent) {
                  onNavigate?.()
                  navigate(MODES[mode].path)
                }
                toast("会话已删除")
              }}
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
