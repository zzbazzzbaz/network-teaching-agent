import { Plus, Search } from "lucide-react"
import { useMemo, useState } from "react"

import type { QuestionDetail, QuestionScope } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import {
  WorkspaceHeader,
  workspaceContentClass,
} from "@/shared/ui/workspace-header"
import { Input } from "@/shared/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select"

import {
  ALL_KNOWLEDGE_POINTS,
  SCOPE_OPTIONS,
  TYPE_OPTIONS,
  knowledgePointIndent,
  questionErrorMessage,
  type QuestionFilterState,
  type TypeFilter,
} from "../model"
import {
  useKnowledgePoints,
  useQuestionCounts,
  useQuestions,
} from "../queries"
import { QuestionCard } from "./QuestionCard"
import { QuestionDetailDialog } from "./QuestionDetailDialog"
import { QuestionEditorDialog } from "./QuestionEditorDialog"
import { useDebouncedValue } from "./useDebouncedValue"

export interface QuestionPanelProps {
  selectedQuestionId?: string
  onSelectQuestion: (id: string | undefined) => void
}

export function QuestionPanel({
  selectedQuestionId,
  onSelectQuestion,
}: QuestionPanelProps) {
  const [scope, setScope] = useState<QuestionScope>("all")
  const [queryInput, setQueryInput] = useState("")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all")
  const [knowledgePointId, setKnowledgePointId] = useState<string>(
    ALL_KNOWLEDGE_POINTS,
  )
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingQuestion, setEditingQuestion] =
    useState<QuestionDetail | null>(null)
  const [detailVersion, setDetailVersion] = useState(0)

  const debouncedQuery = useDebouncedValue(queryInput.trim(), 300)

  const filters = useMemo<QuestionFilterState>(
    () => ({
      query: debouncedQuery,
      questionType: typeFilter,
      knowledgePointId,
    }),
    [debouncedQuery, typeFilter, knowledgePointId],
  )

  const questions = useQuestions(scope, filters)
  const counts = useQuestionCounts(filters)
  const knowledgePointsQuery = useKnowledgePoints()

  const items = questions.data?.pages.flatMap((page) => page.items) ?? []
  const total = questions.data?.pages[0]?.total ?? 0
  const hasActiveFilters =
    scope !== "all" ||
    debouncedQuery.length > 0 ||
    typeFilter !== "all" ||
    knowledgePointId !== ALL_KNOWLEDGE_POINTS

  function resetFilters() {
    setScope("all")
    setQueryInput("")
    setTypeFilter("all")
    setKnowledgePointId(ALL_KNOWLEDGE_POINTS)
  }

  function openCreate() {
    setEditingQuestion(null)
    setEditorOpen(true)
  }

  function closeEditor() {
    setEditorOpen(false)
    setEditingQuestion(null)
  }

  function startEdit(question: QuestionDetail) {
    onSelectQuestion(undefined)
    setEditingQuestion(question)
    setEditorOpen(true)
  }

  function handleSaved(questionId: string, created: boolean) {
    closeEditor()
    if (created) setScope("mine")
    // 保存后重新打开详情，并强制换一个实例，确保答案重新隐藏。
    setDetailVersion((previous) => previous + 1)
    onSelectQuestion(questionId)
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <WorkspaceHeader
        title="题库"
        actions={
          <Button className="h-9 gap-1.5" onClick={openCreate}>
            <Plus className="size-4" aria-hidden="true" />
            新建私有题
          </Button>
        }
      />

      <div className="scroll-slim min-h-0 flex-1 overflow-y-auto">
        <div className={cn(workspaceContentClass, "py-5 lg:py-6")}>
          <div className="mb-4 flex justify-end lg:hidden">
            <Button className="h-10 w-full gap-1.5" onClick={openCreate}>
              <Plus className="size-4" aria-hidden="true" />
              新建私有题
            </Button>
          </div>

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
                  onClick={() => setScope(item.id)}
                  className={cn(
                    "flex h-9 items-center gap-1.5 rounded-sm border px-2.5 text-[12px] font-medium transition-colors sm:h-8",
                    scope === item.id
                      ? "border-line bg-surface text-ink"
                      : "border-transparent text-ink-muted hover:text-ink",
                  )}
                >
                  {item.label}
                  <span className="font-mono text-[9.5px] text-ink-muted">
                    {counts[item.id] ?? "…"}
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
                onChange={(event) => setQueryInput(event.target.value)}
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
                onClick={() => setTypeFilter(item.id)}
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


          <Select
            value={knowledgePointId}
            onValueChange={setKnowledgePointId}
            disabled={knowledgePointsQuery.isPending}
          >
            <SelectTrigger
              size="sm"
              aria-label="按知识点筛选"
              className="h-9 w-full text-[11.5px] sm:w-[210px]"
            >
              <SelectValue placeholder="知识点" className="min-w-0 truncate" />
            </SelectTrigger>
            <SelectContent className="max-h-72">
              <SelectItem value={ALL_KNOWLEDGE_POINTS}>全部知识点</SelectItem>
              {knowledgePointsQuery.data?.nodes.map((node) => (
                <SelectItem key={node.id} value={node.id}>
                  {knowledgePointIndent(node.level)}
                  {node.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {knowledgePointsQuery.isError && (
            <button
              type="button"
              onClick={() => void knowledgePointsQuery.refetch()}
              className="text-[11px] font-medium text-danger underline underline-offset-2"
            >
              知识点加载失败，重试
            </button>
          )}
          <span className="ml-auto text-[11px] tabular-nums text-ink-muted">
            {questions.isPending
              ? "正在加载…"
              : questions.isError
                ? "加载失败"
                : `共 ${total} 题`}
          </span>
        </div>

        {questions.isPending ? (
          <QuestionListSkeleton />
        ) : questions.isError && items.length === 0 ? (
          <QuestionListError
            message={questionErrorMessage(
              questions.error,
              "题目加载失败，请稍后重试。",
            )}
            onRetry={() => void questions.refetch()}
          />
        ) : items.length === 0 ? (
          <QuestionListEmpty
            filtered={hasActiveFilters}
            onReset={resetFilters}
            onCreate={openCreate}
          />
        ) : (
          <>
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {items.map((question) => (
                <QuestionCard
                  key={question.question_id}
                  question={question}
                  onOpen={onSelectQuestion}
                />
              ))}
            </div>

            <div className="mt-4 flex flex-col items-center gap-2">
              <p className="text-[11px] tabular-nums text-ink-muted">
                已显示 {items.length} / 共 {total} 题
              </p>
              {questions.hasNextPage && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-10 sm:h-8"
                  disabled={questions.isFetchingNextPage}
                  onClick={() => void questions.fetchNextPage()}
                >
                  {questions.isFetchingNextPage ? "正在加载…" : "加载更多"}
                </Button>
              )}
            </div>
          </>
        )}
        </div>
      </div>

      {selectedQuestionId && (
        <QuestionDetailDialog
          key={`${selectedQuestionId}:${detailVersion}`}
          questionId={selectedQuestionId}
          onClose={() => onSelectQuestion(undefined)}
          onEdit={startEdit}
        />
      )}

      {editorOpen && (
        <QuestionEditorDialog
          question={editingQuestion}
          defaultKnowledgePointId={
            knowledgePointId === ALL_KNOWLEDGE_POINTS
              ? undefined
              : knowledgePointId
          }
          onClose={closeEditor}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}

function QuestionListSkeleton() {
  return (
    <>
      <p className="sr-only" role="status">
        正在加载题目…
      </p>
      <div
        aria-hidden="true"
        className="mt-5 grid gap-3 md:grid-cols-2"
      >
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

function QuestionListError({
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

function QuestionListEmpty({
  filtered,
  onReset,
  onCreate,
}: {
  filtered: boolean
  onReset: () => void
  onCreate: () => void
}) {
  return (
    <div className="mt-6 rounded-lg border border-line bg-surface px-6 py-14 text-center">
      <p className="text-[13px] text-ink-soft">
        {filtered ? "没有匹配的题目" : "题库还是空的"}
      </p>
      <p className="mt-1 text-[11.5px] leading-5 text-ink-muted">
        {filtered
          ? "换个关键词，或切换来源和题型。"
          : "新建一道私有题，或等待老师发布公共题。"}
      </p>
      {filtered ? (
        <Button
          variant="outline"
          size="sm"
          className="mt-4 h-10 sm:h-8"
          onClick={onReset}
        >
          清除筛选
        </Button>
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="mt-4 h-10 gap-1.5 sm:h-8"
          onClick={onCreate}
        >
          <Plus className="size-3.5" aria-hidden="true" />
          新建私有题
        </Button>
      )}
    </div>
  )
}
