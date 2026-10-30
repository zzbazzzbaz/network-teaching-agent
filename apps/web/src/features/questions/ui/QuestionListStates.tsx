import { Plus } from "lucide-react"
import type { ReactNode } from "react"

import type { QuestionScope } from "@/shared/api/types"
import { Button } from "@/shared/ui/button"

import { SCOPE_OPTIONS } from "../model"

export type EmptyReason = "filtered" | "knowledge-point" | "scope" | "bank"

export function QuestionListSkeleton() {
  return (
    <>
      <p className="sr-only" role="status">
        正在加载题目…
      </p>
      <div aria-hidden="true" className="mt-5 grid gap-3 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="flex min-h-[150px] animate-pulse flex-col rounded-lg border border-line bg-surface p-4"
          >
            <div className="space-y-2">
              <div className="h-3.5 w-full rounded-sm bg-surface-3" />
              <div className="h-3.5 w-5/6 rounded-sm bg-surface-3" />
              <div className="h-3.5 w-2/3 rounded-sm bg-surface-3" />
            </div>
            <div className="mt-auto pt-4">
              <div className="h-3 w-28 rounded-sm bg-surface-3" />
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

export function QuestionListError({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <div
      role="alert"
      className="mt-6 rounded-lg border border-danger-line bg-danger-soft/40 px-6 py-12 text-center"
    >
      <p className="text-[13px] font-medium text-danger">题目加载失败</p>
      <p className="mt-1.5 text-[11.5px] leading-5 text-ink-muted">{message}</p>
      <Button
        variant="outline"
        size="sm"
        className="mt-4 h-10 sm:h-8"
        onClick={onRetry}
      >
        重试
      </Button>
    </div>
  )
}

export function QuestionListEmpty({
  reason,
  scope,
  onReset,
  onClearKnowledgePoint,
  onViewAllScope,
  onCreate,
}: {
  reason: EmptyReason
  scope: QuestionScope
  onReset: () => void
  onClearKnowledgePoint: () => void
  onViewAllScope: () => void
  onCreate: () => void
}) {
  const scopeLabel =
    SCOPE_OPTIONS.find((item) => item.id === scope)?.label ?? "当前"

  if (reason === "filtered") {
    return (
      <EmptyShell
        title="没有匹配的题目"
        description="换个关键词，或切换来源和题型。"
        action={
          <Button
            variant="outline"
            size="sm"
            className="h-10 sm:h-8"
            onClick={onReset}
          >
            清除筛选
          </Button>
        }
      />
    )
  }

  if (reason === "knowledge-point") {
    return (
      <EmptyShell
        title="这个知识点下还没有题目"
        description={
          scope === "all"
            ? "可以在这里新建一道私有题，或查看全部题目。"
            : `${scopeLabel}来源下没有；可以查看全部来源，或查看全部题目。`
        }
        action={
          <div className="flex flex-wrap items-center justify-center gap-2">
            {scope !== "all" && (
              <Button
                variant="outline"
                size="sm"
                className="h-10 sm:h-8"
                onClick={onViewAllScope}
              >
                查看全部来源
              </Button>
            )}
            {scope === "all" && (
              <Button
                size="sm"
                className="h-10 gap-1.5 sm:h-8"
                onClick={onCreate}
              >
                <Plus className="size-3.5" aria-hidden="true" />
                在这里新建
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-10 sm:h-8"
              onClick={onClearKnowledgePoint}
            >
              查看全部题目
            </Button>
          </div>
        }
      />
    )
  }

  if (reason === "scope") {
    return (
      <EmptyShell
        title="当前来源没有题目"
        description="切换来源，看看公共题或我的题。"
        action={
          <Button
            variant="outline"
            size="sm"
            className="h-10 sm:h-8"
            onClick={onViewAllScope}
          >
            查看全部
          </Button>
        }
      />
    )
  }

  return (
    <EmptyShell
      title="题库还是空的"
      description="新建一道私有题，或等待老师发布公共题。"
      action={
        <Button
          variant="outline"
          size="sm"
          className="h-10 gap-1.5 sm:h-8"
          onClick={onCreate}
        >
          <Plus className="size-3.5" aria-hidden="true" />
          新建私有题
        </Button>
      }
    />
  )
}

function EmptyShell({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action: ReactNode
}) {
  return (
    <div className="mt-6 rounded-lg border border-line bg-surface px-6 py-14 text-center">
      <p className="text-[13px] text-ink-soft">{title}</p>
      <p className="mt-1 text-[11.5px] leading-5 text-ink-muted">
        {description}
      </p>
      <div className="mt-4">{action}</div>
    </div>
  )
}
