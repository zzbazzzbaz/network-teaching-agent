import { Plus } from "lucide-react"
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import { toast } from "sonner"

import { useKnowledgePoints } from "@/features/course"
import type { QuestionDetail, QuestionScope } from "@/shared/api/types"
import { readStorage, writeStorage } from "@/shared/lib/storage"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
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
  questionErrorMessage,
  type QuestionFilterState,
  type TypeFilter,
} from "../model"
import {
  useKnowledgePointCounts,
  useQuestions,
  type KnowledgePointCountFilters,
} from "../queries"
import { QuestionFiltersBar } from "./QuestionFiltersBar"
import { KnowledgePointSidebar } from "./KnowledgePointSidebar"
import { QuestionCard } from "./QuestionCard"
import { QuestionDetailDialog } from "./QuestionDetailDialog"
import { QuestionEditorDialog } from "./QuestionEditorDialog"
import {
  QuestionListEmpty,
  QuestionListError,
  QuestionListSkeleton,
  type EmptyReason,
} from "./QuestionListStates"
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
  return readStorage(SHOW_ALL_KEY) === "1"
}

function writeShowEmptyPreference(value: boolean): void {
  writeStorage(SHOW_ALL_KEY, value ? "1" : "0")
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
  }, [debouncedQuery, knowledgePointId, scope, typeFilter])

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

  const scopeCounts: Record<QuestionScope, string> = {
    all: scopeCountLabel("all"),
    public: scopeCountLabel("public"),
    mine: scopeCountLabel("mine"),
  }

  const selectKnowledgePoint = useCallback(
    (id: string | undefined) => {
      setMobileTreeOpen(false)
      onSelectKnowledgePoint(id)
    },
    [onSelectKnowledgePoint],
  )

  const retryKnowledgePoints = useCallback(() => {
    void knowledgePointsQuery.refetch()
  }, [knowledgePointsQuery.refetch])

  const retryCounts = useCallback(() => {
    void countsQuery.refetch()
  }, [countsQuery.refetch])

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
    onRetry: retryKnowledgePoints,
    countsPending: countsQuery.isPending,
    countsBusy: countsQuery.isFetching && !countsQuery.isPending,
    countsError: countsQuery.isError,
    onRetryCounts: retryCounts,
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

            <QuestionFiltersBar
              scope={scope}
              onScopeChange={setScope}
              queryInput={queryInput}
              onQueryChange={setQueryInput}
              typeFilter={typeFilter}
              onTypeChange={setTypeFilter}
              mobileKnowledgePointLabel={mobileKnowledgePointLabel}
              currentCount={currentCount}
              knowledgePointsPending={knowledgePointsQuery.isPending}
              onOpenMobileTree={() => setMobileTreeOpen(true)}
              scopeCounts={scopeCounts}
              total={total}
              isPending={questions.isPending}
              isError={questions.isError}
            />

            {questions.isError && items.length > 0 ? (
              <div className="mt-3 flex flex-wrap items-center gap-2 rounded-md border border-danger-line bg-danger-soft/40 px-3 py-2 text-[11px] text-danger">
                <span>题目刷新失败，当前显示的是上次结果。</span>
                <button
                  type="button"
                  onClick={() => void questions.refetch()}
                  className="font-medium underline underline-offset-2"
                >
                  重试
                </button>
              </div>
            ) : null}

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
