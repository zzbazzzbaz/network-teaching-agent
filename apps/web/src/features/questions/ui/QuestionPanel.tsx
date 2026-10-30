import { ChevronDown, FolderTree, Plus, Search } from "lucide-react"
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { toast } from "sonner"

import { useKnowledgePoints } from "@/features/course"
import type { QuestionDetail, QuestionScope } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/shared/ui/sheet"
import {
  WorkspaceHeader,
  workspaceContentClass,
} from "@/shared/ui/workspace-header"

import {
  ALL_KNOWLEDGE_POINTS,
  SCOPE_OPTIONS,
  TYPE_OPTIONS,
  questionErrorMessage,
  type QuestionFilterState,
  type TypeFilter,
} from "../model"
import {
  useKnowledgePointCounts,
  useQuestions,
  type KnowledgePointCountFilters,
} from "../queries"
import { KnowledgePointSidebar } from "./KnowledgePointSidebar"
import { QuestionCard } from "./QuestionCard"
import { QuestionDetailDialog } from "./QuestionDetailDialog"
import { QuestionEditorDialog } from "./QuestionEditorDialog"
import { useDebouncedValue } from "./useDebouncedValue"

const SHOW_ALL_KEY = "question-bank.show-all-knowledge-points"

export interface QuestionPanelProps {
  selectedQuestionId?: string
  selectedKnowledgePointId?: string
  onSelectQuestion: (id: string | undefined) => void
  onSelectKnowledgePoint: (
    id: string | undefined,
    options?: { replace?: boolean },
  ) => void
}

function readShowEmptyPreference(): boolean {
  try {
    return window.localStorage.getItem(SHOW_ALL_KEY) === "1"
  } catch {
    return false
  }
}

function writeShowEmptyPreference(value: boolean): void {
  try {
    window.localStorage.setItem(SHOW_ALL_KEY, value ? "1" : "0")
  } catch {
    // 隐私模式或禁用 storage 时忽略，只影响下次是否记住开关。
  }
}

export function QuestionPanel({
  selectedQuestionId,
  selectedKnowledgePointId,
  onSelectQuestion,
  onSelectKnowledgePoint,
}: QuestionPanelProps) {
  const [scope, setScope] = useState<QuestionScope>("all")
  const [queryInput, setQueryInput] = useState("")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all")
  const [showEmpty, setShowEmpty] = useState(readShowEmptyPreference)
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingQuestion, setEditingQuestion] =
    useState<QuestionDetail | null>(null)
  const [mobileTreeOpen, setMobileTreeOpen] = useState(false)
  const [detailVersion, setDetailVersion] = useState(0)
  const invalidKpRef = useRef<string | null>(null)
  const listScrollRef = useRef<HTMLDivElement | null>(null)

  const debouncedQuery = useDebouncedValue(queryInput.trim(), 300)
  const knowledgePointsQuery = useKnowledgePoints()
  const knowledgePointNodes = knowledgePointsQuery.data?.nodes ?? []

  const kpExists =
    !!selectedKnowledgePointId &&
    knowledgePointNodes.some(
      (node) => node.id === selectedKnowledgePointId,
    )
  const knowledgePointId =
    selectedKnowledgePointId && kpExists
      ? selectedKnowledgePointId
      : ALL_KNOWLEDGE_POINTS
  const hasKnowledgePoint =
    knowledgePointId !== ALL_KNOWLEDGE_POINTS
  const knowledgePointsReady =
    !selectedKnowledgePointId ||
    Boolean(knowledgePointsQuery.data) ||
    knowledgePointsQuery.isError

  const filters = useMemo<QuestionFilterState>(
    () => ({
      query: debouncedQuery,
      questionType: typeFilter,
      knowledgePointId,
    }),
    [debouncedQuery, typeFilter, knowledgePointId],
  )
  const treeCountFilters = useMemo<KnowledgePointCountFilters>(
    () => ({ query: debouncedQuery, questionType: typeFilter }),
    [debouncedQuery, typeFilter],
  )

  const questions = useQuestions(scope, filters, knowledgePointsReady)
  const countsQuery = useKnowledgePointCounts(treeCountFilters)

  const selectedKnowledgePoint = knowledgePointNodes.find(
    (node) => node.id === knowledgePointId,
  )
  const knowledgePointLabel = hasKnowledgePoint
    ? selectedKnowledgePoint
      ? `${selectedKnowledgePoint.id} ${selectedKnowledgePoint.title}`
      : "全部题目"
    : "全部题目"

  const countsForTree = countsQuery.isError
    ? undefined
    : countsQuery.data?.counts[scope]
  const scopeTotal = countsQuery.isError
    ? undefined
    : countsQuery.data?.totals[scope]
  const currentCount = hasKnowledgePoint
    ? countsForTree?.[knowledgePointId]
    : scopeTotal
  const mobileKnowledgePointLabel = knowledgePointsQuery.isPending
    ? "正在加载知识点…"
    : knowledgePointLabel

  const items = questions.data?.pages.flatMap((page) => page.items) ?? []
  const total = questions.data?.pages[0]?.total ?? 0
  const hasResultFilters =
    debouncedQuery.length > 0 || typeFilter !== "all"
  const emptyReason: EmptyReason = hasResultFilters
    ? "filtered"
    : hasKnowledgePoint
      ? "knowledge-point"
      : scope !== "all"
        ? "scope"
        : "bank"

  useEffect(() => {
    writeShowEmptyPreference(showEmpty)
  }, [showEmpty])

  useEffect(() => {
    listScrollRef.current?.scrollTo({ top: 0 })
  }, [knowledgePointId])

  useEffect(() => {
    if (!selectedKnowledgePointId) {
      invalidKpRef.current = null
      return
    }
    if (!knowledgePointsQuery.data) return
    const exists = knowledgePointsQuery.data.nodes.some(
      (node) => node.id === selectedKnowledgePointId,
    )
    if (exists) {
      invalidKpRef.current = null
      return
    }
    if (invalidKpRef.current === selectedKnowledgePointId) return
    invalidKpRef.current = selectedKnowledgePointId
    toast.error("知识点不存在，已显示全部题目")
    onSelectKnowledgePoint(undefined, { replace: true })
  }, [
    knowledgePointsQuery.data,
    onSelectKnowledgePoint,
    selectedKnowledgePointId,
  ])

  function scopeCountLabel(scopeId: QuestionScope): string {
    if (countsQuery.isError) return "–"
    if (!countsQuery.data) return "…"
    if (hasKnowledgePoint) {
      return String(
        countsQuery.data.counts[scopeId]?.[knowledgePointId] ?? 0,
      )
    }
    return String(countsQuery.data.totals[scopeId])
  }

  function selectKnowledgePoint(id: string | undefined) {
    setMobileTreeOpen(false)
    onSelectKnowledgePoint(id)
  }

  function resetFilters() {
    setScope("all")
    setQueryInput("")
    setTypeFilter("all")
    selectKnowledgePoint(undefined)
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

  const sidebarProps = {
    nodes: knowledgePointNodes,
    value: hasKnowledgePoint ? knowledgePointId : undefined,
    counts: countsForTree,
    total: scopeTotal,
    hasQuery: debouncedQuery.length > 0,
    showEmpty,
    onShowEmptyChange: setShowEmpty,
    onSelect: selectKnowledgePoint,
    isPending: knowledgePointsQuery.isPending,
    isError: knowledgePointsQuery.isError,
    onRetry: () => void knowledgePointsQuery.refetch(),
    countsPending: countsQuery.isPending,
    countsBusy: countsQuery.isFetching && !countsQuery.isPending,
    countsError: countsQuery.isError,
    onRetryCounts: () => void countsQuery.refetch(),
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

      <div className="flex min-h-0 flex-1">
        <KnowledgePointSidebar variant="desktop" {...sidebarProps} />

        <div
          ref={listScrollRef}
          className="scroll-slim min-h-0 flex-1 overflow-y-auto"
        >
          <div className={cn(workspaceContentClass, "py-5 lg:py-6")}>
            <div className="mb-4 flex justify-end lg:hidden">
              <Button className="h-10 w-full gap-1.5" onClick={openCreate}>
                <Plus className="size-4" aria-hidden="true" />
                新建私有题
              </Button>
            </div>

            {knowledgePointsQuery.isError && (
              <div className="mb-3 flex flex-wrap items-center gap-2 rounded-md border border-danger-line bg-danger-soft/40 px-3 py-2 text-[11px] text-danger">
                <span>知识点目录加载失败，已显示全部题目。</span>
                <button
                  type="button"
                  onClick={() => void knowledgePointsQuery.refetch()}
                  className="font-medium underline underline-offset-2"
                >
                  重试
                </button>
              </div>
            )}

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
                        {scopeCountLabel(item.id)}
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

              <Button
                variant="outline"
                aria-label="按知识点筛选"
                disabled={knowledgePointsQuery.isPending}
                onClick={() => setMobileTreeOpen(true)}
                className="h-9 w-full justify-between gap-1.5 px-2.5 text-[11.5px] font-medium sm:w-[230px] lg:hidden"
              >
                <span className="flex min-w-0 items-center gap-1.5">
                  <FolderTree
                    className="size-3.5 shrink-0 text-ink-muted"
                    aria-hidden="true"
                  />
                  <span className="truncate">
                    {mobileKnowledgePointLabel}
                    {!knowledgePointsQuery.isPending &&
                    currentCount !== undefined
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
                reason={emptyReason}
                scope={scope}
                onReset={resetFilters}
                onClearKnowledgePoint={() =>
                  selectKnowledgePoint(undefined)
                }
                onViewAllScope={() => setScope("all")}
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
                      {questions.isFetchingNextPage
                        ? "正在加载…"
                        : "加载更多"}
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <Sheet open={mobileTreeOpen} onOpenChange={setMobileTreeOpen}>
        <SheetContent side="left" className="p-0">
          <SheetHeader>
            <SheetTitle>知识点</SheetTitle>
            <SheetDescription className="sr-only">
              按教材目录筛选题目
            </SheetDescription>
          </SheetHeader>
          <KnowledgePointSidebar variant="sheet" {...sidebarProps} />
        </SheetContent>
      </Sheet>

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
            hasKnowledgePoint ? knowledgePointId : undefined
          }
          onClose={closeEditor}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}

type EmptyReason = "filtered" | "knowledge-point" | "scope" | "bank"

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
