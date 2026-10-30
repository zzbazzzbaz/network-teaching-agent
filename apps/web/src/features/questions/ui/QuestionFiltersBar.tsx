import { ChevronDown, FolderTree, Search } from "lucide-react"

import type { QuestionScope } from "@/shared/api/types"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { cn } from "@/shared/lib/utils"

import { SCOPE_OPTIONS, TYPE_OPTIONS, type TypeFilter } from "../model"

export function QuestionFiltersBar({
  scope,
  onScopeChange,
  queryInput,
  onQueryChange,
  typeFilter,
  onTypeChange,
  mobileKnowledgePointLabel,
  currentCount,
  knowledgePointsPending,
  onOpenMobileTree,
  scopeCounts,
  total,
  isPending,
  isError,
}: {
  scope: QuestionScope
  onScopeChange: (scope: QuestionScope) => void
  queryInput: string
  onQueryChange: (value: string) => void
  typeFilter: TypeFilter
  onTypeChange: (type: TypeFilter) => void
  mobileKnowledgePointLabel: string
  currentCount?: number
  knowledgePointsPending: boolean
  onOpenMobileTree: () => void
  scopeCounts: Record<QuestionScope, string>
  total: number
  isPending: boolean
  isError: boolean
}) {
  return (
    <>
      <div className="border-b border-line pb-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <div
            role="group"
            aria-label="题目来源"
            className="flex items-center gap-0.5 rounded-md bg-surface-3 p-0.5"
          >
            {SCOPE_OPTIONS.map((item) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={scope === item.id}
                onClick={() => onScopeChange(item.id)}
                className={cn(
                  "flex h-9 items-center gap-1.5 rounded-sm border px-2.5 text-[12px] font-medium transition-colors sm:h-8",
                  scope === item.id
                    ? "border-line bg-surface text-ink"
                    : "border-transparent text-ink-muted hover:text-ink",
                )}
              >
                {item.label}
                <span className="font-mono text-[9.5px] text-ink-muted">
                  {scopeCounts[item.id]}
                </span>
              </button>
            ))}
          </div>

          <div className="relative ml-auto w-full sm:w-[300px]">
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-ink-muted"
              aria-hidden="true"
            />
            <Input
              value={queryInput}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="搜索题干…"
              aria-label="搜索题干"
              autoComplete="off"
              spellCheck={false}
              maxLength={100}
              className="h-10 pl-8 text-[16px] sm:h-9 sm:text-[12.5px]"
            />
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <div
          role="group"
          aria-label="题型"
          className="flex items-center gap-0.5 rounded-md bg-surface-3 p-0.5"
        >
          {TYPE_OPTIONS.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={typeFilter === item.id}
              onClick={() => onTypeChange(item.id)}
              className={cn(
                "h-9 rounded-sm border px-2.5 text-[11.5px] font-medium transition-colors sm:h-8",
                typeFilter === item.id
                  ? "border-line bg-surface text-ink"
                  : "border-transparent text-ink-muted hover:text-ink",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>

        <Button
          variant="outline"
          aria-label="按知识点筛选"
          disabled={knowledgePointsPending}
          onClick={onOpenMobileTree}
          className="h-9 w-full justify-between gap-1.5 px-2.5 text-[11.5px] font-medium sm:w-[230px] lg:hidden"
        >
          <span className="flex min-w-0 items-center gap-1.5">
            <FolderTree
              className="size-3.5 shrink-0 text-ink-muted"
              aria-hidden="true"
            />
            <span className="truncate">
              {mobileKnowledgePointLabel}
              {!knowledgePointsPending && currentCount !== undefined
                ? ` · ${currentCount} 题`
                : ""}
            </span>
          </span>
          <ChevronDown
            className="size-3.5 shrink-0 text-ink-muted"
            aria-hidden="true"
          />
        </Button>

        <span className="ml-auto text-[11px] tabular-nums text-ink-muted">
          {isPending ? "正在加载…" : isError ? "加载失败" : `共 ${total} 题`}
        </span>
      </div>
    </>
  )
}
