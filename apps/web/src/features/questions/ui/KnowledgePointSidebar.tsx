import { Check, Info } from "lucide-react"
import { memo } from "react"

import type { KnowledgePoint } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/shared/ui/tooltip"

import { KnowledgePointTree } from "./KnowledgePointTree"

export interface KnowledgePointSidebarProps {
  variant: "desktop" | "sheet"
  className?: string
  nodes: KnowledgePoint[]
  value?: string
  /** 当前 scope 的知识点计数；undefined 表示统计不可用。 */
  counts?: Record<string, number>
  /** 当前 scope 的总题量；对应“全部题目”行。 */
  total?: number
  hasQuery: boolean
  showEmpty: boolean
  onShowEmptyChange: (value: boolean) => void
  onSelect: (id: string | undefined) => void
  isPending: boolean
  isError: boolean
  onRetry: () => void
  countsPending: boolean
  countsBusy?: boolean
  countsError: boolean
  onRetryCounts: () => void
}

export const KnowledgePointSidebar = memo(function KnowledgePointSidebar({
  variant,
  className,
  nodes,
  value,
  counts,
  total,
  hasQuery,
  showEmpty,
  onShowEmptyChange,
  onSelect,
  isPending,
  isError,
  onRetry,
  countsPending,
  countsBusy,
  countsError,
  onRetryCounts,
}: KnowledgePointSidebarProps) {
  const treeCounts = countsError ? undefined : counts
  const hasCounts = treeCounts !== undefined
  const initialLoading =
    isPending || (countsPending && !hasCounts && !countsError)
  const treeIsEmpty =
    hasCounts && !showEmpty && Object.keys(treeCounts).length === 0
  const totalText =
    total !== undefined ? String(total) : countsError ? "–" : "…"

  return (
    <div
      className={cn(
        "min-h-0 flex-col bg-surface",
        variant === "desktop"
          ? "hidden shrink-0 border-r border-line lg:flex lg:w-[260px] xl:w-[280px]"
          : "flex min-h-0 w-full flex-1",
        className,
      )}
    >
      {variant === "desktop" && (
        <div className="flex h-11 shrink-0 items-end px-4 pb-2">
          <h3 className="text-[11px] font-semibold tracking-[0.08em] text-ink-muted uppercase">
            知识点
          </h3>
        </div>
      )}

      <div className="shrink-0 px-2 pt-1">
        <button
          type="button"
          aria-current={value ? undefined : "true"}
          onClick={() => onSelect(undefined)}
          className={cn(
            "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-[12px] transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/30",
            value
              ? "text-ink-soft hover:bg-surface-2 hover:text-ink"
              : "bg-link-soft text-link-strong",
          )}
        >
          <span className="flex-1 font-medium">全部题目</span>
          <span
            className={cn(
              "font-mono text-[10px] tabular-nums",
              value ? "text-ink-muted" : "text-link",
            )}
          >
            {totalText}
          </span>
        </button>
      </div>

      <div className="scroll-slim min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {isError ? (
          <div className="rounded-lg border border-danger-line bg-danger-soft/40 px-3 py-4 text-center">
            <p className="text-[11.5px] font-medium text-danger">
              知识点目录加载失败
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3 h-9"
              onClick={onRetry}
            >
              重试
            </Button>
          </div>
        ) : initialLoading ? (
          <TreeSkeleton />
        ) : (
          <>
            {treeIsEmpty && (
              <div className="mb-2 rounded-lg border border-line bg-surface-2 px-3 py-3 text-center">
                <p className="text-[11.5px] text-ink-muted">
                  {hasQuery ? "没有匹配的知识点" : "当前范围没有题目"}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2.5 h-8"
                  onClick={() => onShowEmptyChange(true)}
                >
                  显示完整目录
                </Button>
              </div>
            )}
            <div
              aria-busy={countsBusy || undefined}
              className={cn(
                "transition-opacity",
                countsBusy && "opacity-70",
              )}
            >
              <KnowledgePointTree
                nodes={nodes}
                value={value}
                counts={treeCounts}
                showEmpty={showEmpty}
                defaultExpandLevel={1}
                onSelect={onSelect}
              />
            </div>
            {countsError && (
              <button
                type="button"
                onClick={onRetryCounts}
                className="mt-2 w-full rounded-sm px-2 py-1.5 text-left text-[11px] font-medium text-danger underline-offset-2 hover:underline"
              >
                题量统计加载失败，重试
              </button>
            )}
          </>
        )}
      </div>

      <div className="shrink-0 border-t border-line px-3 py-2.5">
        <button
          type="button"
          aria-pressed={showEmpty}
          disabled={!hasCounts}
          onClick={() => onShowEmptyChange(!showEmpty)}
          className={cn(
            "flex items-center gap-1.5 text-[11px] font-medium transition-colors",
            hasCounts
              ? "text-ink-muted hover:text-ink"
              : "cursor-default text-ink-muted/50",
          )}
        >
          <span
            className={cn(
              "flex size-3.5 items-center justify-center rounded-[3px] border",
              showEmpty
                ? "border-link bg-link text-white"
                : "border-line-strong bg-surface",
            )}
            aria-hidden="true"
          >
            {showEmpty && <Check className="size-2.5" strokeWidth={3} />}
          </span>
          显示完整目录
        </button>
        <div className="mt-1.5 flex items-center gap-1 text-[10.5px] text-ink-muted">
          <span>按主知识点归类</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                tabIndex={0}
                className="inline-flex rounded-full text-ink-muted outline-none hover:text-ink focus-visible:ring-2 focus-visible:ring-ring/30"
                aria-label="知识点计数说明"
              >
                <Info className="size-3" aria-hidden="true" />
              </span>
            </TooltipTrigger>
            <TooltipContent>
              辅知识点不参与树和计数，只在题目详情展示。
            </TooltipContent>
          </Tooltip>
        </div>
      </div>
    </div>
  )
})

function TreeSkeleton() {
  return (
    <>
      <p className="sr-only" role="status">
        正在加载知识点…
      </p>
      <div aria-hidden="true" className="space-y-2 px-1">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="flex items-center gap-2">
            <div className="size-4 shrink-0 animate-pulse rounded-sm bg-surface-3" />
            <div
              className="h-3 animate-pulse rounded-sm bg-surface-3"
              style={{ width: `${56 + ((index * 13) % 34)}%` }}
            />
          </div>
        ))}
      </div>
    </>
  )
}
