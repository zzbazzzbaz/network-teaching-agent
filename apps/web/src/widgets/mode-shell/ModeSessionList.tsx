import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"

import type { Session } from "@/shared/api/types"
import { DEFAULT_SESSION_TITLE } from "@/features/sessions"
import { cn, formatDate, formatTime, relativeDay } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu"

export function ModeSessionList({
  sessions,
  total,
  activeSessionId,
  isLoading,
  isError,
  hasNextPage,
  isFetchingNextPage,
  onSelect,
  onRename,
  onDelete,
  onRetry,
  onLoadMore,
  onNew,
}: {
  sessions: Session[]
  total: number
  activeSessionId?: string
  isLoading: boolean
  isError: boolean
  hasNextPage: boolean
  isFetchingNextPage: boolean
  onSelect: (sessionId: string) => void
  onRename: (session: Session) => void
  onDelete: (session: Session) => void
  onRetry: () => void
  onLoadMore: () => void
  onNew: () => void
}) {
  return (
    <div className="mt-4 flex min-h-0 flex-1 flex-col border-t border-line px-3 pt-3">
      <div className="flex items-baseline justify-between px-1 pb-1">
        <span className="text-[10.5px] font-medium text-ink-muted">会话</span>
        <span className="font-mono text-[9.5px] text-ink-muted">{total}</span>
      </div>

      <nav
        aria-label="会话列表"
        className="scroll-slim -mx-1 min-h-0 flex-1 overflow-y-auto px-1 pb-2"
      >
        {isLoading ? (
          <div className="space-y-2 px-1 py-2" aria-label="会话加载中">
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="h-[54px] animate-pulse rounded-md bg-surface-3"
              />
            ))}
          </div>
        ) : isError && sessions.length === 0 ? (
          <div className="px-2 py-8 text-center">
            <p className="text-[12px] text-ink-muted">会话加载失败</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={onRetry}
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
              onClick={onNew}
            >
              新建第一个会话
            </Button>
          </div>
        ) : (
          <>
            <ul className="space-y-1">
              {sessions.map((session) => {
                const active = session.session_id === activeSessionId
                return (
                  <li
                    key={session.session_id}
                    className="group/item relative"
                  >
                    <button
                      type="button"
                      onClick={() => onSelect(session.session_id)}
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
                      <span className="flex items-center pr-[4.25rem]">
                        <span
                          className={cn(
                            "min-w-0 flex-1 truncate text-[12.5px] leading-5",
                            active
                              ? "font-medium text-ink"
                              : "text-ink-soft",
                          )}
                        >
                          {session.title || DEFAULT_SESSION_TITLE}
                        </span>
                      </span>
                      <time
                        dateTime={session.updated_at}
                        className="absolute top-1/2 right-2.5 -translate-y-1/2 text-[9.5px] tabular-nums text-ink-muted"
                      >
                        {relativeDay(session.updated_at) === "今天"
                          ? formatTime(session.updated_at)
                          : formatDate(session.updated_at)}
                      </time>
                    </button>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          type="button"
                          aria-label={`管理会话「${session.title || DEFAULT_SESSION_TITLE}」`}
                          className="absolute top-1/2 right-10 flex size-7 -translate-y-1/2 items-center justify-center rounded-sm text-ink-muted opacity-100 transition-opacity hover:bg-surface-3 hover:text-ink focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring/30 lg:opacity-0 lg:group-hover/item:opacity-100"
                        >
                          <MoreHorizontal
                            className="size-3.5"
                            aria-hidden="true"
                          />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start" className="w-36">
                        <DropdownMenuItem onSelect={() => onRename(session)}>
                          <Pencil className="size-3.5" aria-hidden="true" />
                          重命名
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          variant="destructive"
                          onSelect={() => onDelete(session)}
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
            {hasNextPage && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 w-full text-[11.5px]"
                disabled={isFetchingNextPage}
                onClick={onLoadMore}
              >
                {isFetchingNextPage ? "加载中…" : "加载更多"}
              </Button>
            )}
          </>
        )}
      </nav>
    </div>
  )
}
