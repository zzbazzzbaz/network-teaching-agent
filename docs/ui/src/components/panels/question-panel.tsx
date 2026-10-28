import {
  Check,
  Clock,
  Eye,
  Lock,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react"
import { useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { toast } from "sonner"

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
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  knowledgePoints,
  kpTitle,
  type Question,
} from "@/lib/mock"
import { useStore } from "@/lib/store"
import { cn, formatDate, formatDateTime } from "@/lib/utils"

import { QuestionEditor } from "@/components/panels/question-editor"

const SCOPES = [
  { id: "all", label: "全部" },
  { id: "public", label: "公共" },
  { id: "mine", label: "我的" },
] as const

const TYPES = [
  { id: "all", label: "全部" },
  { id: "single_choice", label: "单选" },
  { id: "short_answer", label: "简答" },
] as const

type Scope = (typeof SCOPES)[number]["id"]
type TypeFilter = (typeof TYPES)[number]["id"]

export function QuestionPanel() {
  const { questionList, deleteQuestion } = useStore()
  const [params, setParams] = useSearchParams()

  const selectedId = params.get("question")
  const selected = questionList.find((question) => question.id === selectedId)

  const [scope, setScope] = useState<Scope>("all")
  const [query, setQuery] = useState("")
  const [kp, setKp] = useState("all")
  const [type, setType] = useState<TypeFilter>("all")
  const [revealedId, setRevealedId] = useState<string | null>(null)
  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<Question | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Question | null>(null)

  const revealed = revealedId === selectedId

  const counts = useMemo(
    () => ({
      all: questionList.length,
      public: questionList.filter((question) => question.origin === "public").length,
      mine: questionList.filter((question) => question.origin === "mine").length,
    }),
    [questionList],
  )

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase()
    return questionList.filter((question) => {
      if (scope !== "all" && question.origin !== scope) return false
      if (type !== "all" && question.type !== type) return false
      if (kp !== "all" && question.kpId !== kp) return false
      if (keyword && !question.stem.toLowerCase().includes(keyword)) return false
      return true
    })
  }, [questionList, scope, type, kp, query])

  function closeDetail() {
    const next = new URLSearchParams(params)
    next.delete("question")
    setParams(next)
    setRevealedId(null)
  }

  function resetFilters() {
    setScope("all")
    setType("all")
    setQuery("")
    setKp("all")
  }

  function openEditor(question: Question | null) {
    setEditing(question)
    setEditorOpen(true)
  }

  return (
    <div className="scroll-slim h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-[960px] px-5 py-7 lg:px-10 lg:py-9">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-[24px] leading-tight font-semibold tracking-[-0.015em] text-ink">
            题库
          </h2>
          <Button className="h-10 gap-1.5" onClick={() => openEditor(null)}>
            <Plus className="size-4" aria-hidden="true" />
            新建私有题
          </Button>
        </div>

        <div className="mt-6 border-b border-line pb-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <div
              role="group"
              aria-label="题目来源"
              className="flex items-center gap-0.5 rounded-md bg-surface-3 p-0.5"
            >
              {SCOPES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={scope === item.id}
                  onClick={() => setScope(item.id)}
                  className={cn(
                    "flex h-8 items-center gap-1.5 rounded-sm border px-2.5 text-[12px] font-medium transition-colors",
                    scope === item.id
                      ? "border-line bg-surface text-ink"
                      : "border-transparent text-ink-muted hover:text-ink",
                  )}
                >
                  {item.label}
                  <span className="font-mono text-[9.5px] text-ink-muted">
                    {counts[item.id]}
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
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索题干…"
                aria-label="搜索题干"
                autoComplete="off"
                spellCheck={false}
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
            {TYPES.map((item) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={type === item.id}
                onClick={() => setType(item.id)}
                className={cn(
                  "h-8 rounded-sm border px-2.5 text-[11.5px] font-medium transition-colors",
                  type === item.id
                    ? "border-line bg-surface text-ink"
                    : "border-transparent text-ink-muted hover:text-ink",
                )}
              >
                {item.label}
              </button>
            ))}
          </div>

          <Select value={kp} onValueChange={setKp}>
            <SelectTrigger
              size="sm"
              aria-label="按知识点筛选"
              className="h-9 min-w-0 w-[180px] text-[11.5px]"
            >
              <SelectValue placeholder="知识点" />
            </SelectTrigger>
            <SelectContent className="max-h-72">
              <SelectItem value="all">全部知识点</SelectItem>
              {knowledgePoints.map((point) => (
                <SelectItem key={point.id} value={point.id}>
                  {"\u00A0".repeat(Math.max(0, point.level - 1) * 2)}
                  {point.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <span className="ml-auto hidden text-[11px] tabular-nums text-ink-muted sm:block">
            共 {filtered.length} 题
          </span>
        </div>

        {filtered.length === 0 ? (
          <div className="mt-6 rounded-lg border border-line bg-surface px-6 py-14 text-center">
            <p className="text-[13px] text-ink-soft">没有匹配的题目</p>
            <p className="mt-1 text-[11.5px] text-ink-muted">
              换个关键词，或切换来源和题型。
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={resetFilters}
            >
              清除筛选
            </Button>
          </div>
        ) : (
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {filtered.map((question) => (
              <Link
                key={question.id}
                to={`?panel=questions&question=${question.id}`}
                className="group flex min-h-[150px] flex-col rounded-lg border border-line bg-surface p-4 transition-colors hover:border-link-line focus-visible:ring-2 focus-visible:ring-ring/30"
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="muted">
                    {question.type === "single_choice" ? "单选" : "简答"}
                  </Badge>
                  <Badge
                    variant={question.origin === "public" ? "outline" : "default"}
                  >
                    {question.origin === "public" ? "公共" : "我的"}
                  </Badge>
                  <span className="ml-auto truncate text-[10.5px] text-ink-muted">
                    {kpTitle(question.kpId)}
                  </span>
                </div>

                <p className="mt-3 line-clamp-3 text-[13.5px] leading-6 text-ink">
                  {question.stem}
                </p>

                <div className="mt-auto flex items-center gap-1.5 pt-4 text-[10.5px] text-ink-muted">
                  {question.origin === "mine" && (
                    <>
                      <Clock className="size-3" aria-hidden="true" />
                      <span>
                        {question.lastAttemptAt
                          ? `上次作答 ${formatDate(question.lastAttemptAt)}`
                          : "还没有作答记录"}
                      </span>
                    </>
                  )}
                  <span className="ml-auto inline-flex items-center gap-1 text-ink-muted transition-colors group-hover:text-link">
                    查看
                    <Eye className="size-3" aria-hidden="true" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <Dialog
        open={Boolean(selected)}
        onOpenChange={(open) => {
          if (!open) closeDetail()
        }}
      >
        <DialogContent className="max-w-2xl">
          {selected && (
            <>
              <DialogHeader>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="muted">
                    {selected.type === "single_choice" ? "单选" : "简答"}
                  </Badge>
                  <Badge variant={selected.origin === "public" ? "outline" : "default"}>
                    {selected.origin === "public" ? "公共" : "我的"}
                  </Badge>
                  <span className="text-[11px] text-ink-muted">
                    {kpTitle(selected.kpId)}
                  </span>
                </div>
                <DialogTitle className="mt-1.5 pr-5 text-[15px] leading-7 font-medium">
                  {selected.stem}
                </DialogTitle>
                <DialogDescription className="sr-only">
                  题目详情与答案
                </DialogDescription>
              </DialogHeader>

              {selected.type === "single_choice" && selected.options && (
                <ol className="mt-1 space-y-2">
                  {selected.options.map((option) => {
                    const letter = option.charAt(0)
                    const isCorrect = revealed && selected.correctOption === letter
                    return (
                      <li
                        key={option}
                        className={cn(
                          "flex items-start gap-2 rounded-md border px-3 py-2 text-[12.5px] leading-5",
                          isCorrect
                            ? "border-link-line bg-link-soft text-link-strong"
                            : "border-line bg-surface text-ink-soft",
                        )}
                      >
                        {isCorrect ? (
                          <Check
                            className="mt-0.5 size-3.5 shrink-0"
                            aria-hidden="true"
                          />
                        ) : (
                          <span className="mt-0.5 w-3.5 shrink-0 font-mono text-[10.5px] text-ink-muted">
                            {letter}
                          </span>
                        )}
                        <span>{option.replace(/^[A-F][.、]\s*/, "")}</span>
                      </li>
                    )
                  })}
                </ol>
              )}

              <div>
                {!revealed ? (
                  <div className="rounded-md border border-dashed border-line-strong bg-surface-2/50 px-3 py-3">
                    <div className="flex items-center gap-2 text-[11.5px] text-ink-muted">
                      <Lock className="size-3.5" aria-hidden="true" />
                      答案默认隐藏，查看后才显示。
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2.5 h-10 gap-1.5 sm:h-8"
                      onClick={() => setRevealedId(selected.id)}
                    >
                      <Eye className="size-3.5" aria-hidden="true" />
                      查看答案
                    </Button>
                  </div>
                ) : (
                  <div className="rounded-md border border-link-line bg-link-soft/50 px-3 py-3">
                    <div className="flex items-center gap-1.5 text-[11px] font-medium text-link-strong">
                      <Check className="size-3.5" aria-hidden="true" />
                      {selected.type === "single_choice"
                        ? `正确答案：${selected.correctOption}`
                        : "参考答案"}
                    </div>
                    <p className="mt-1.5 text-[12.5px] leading-6 whitespace-pre-wrap text-ink-soft">
                      {selected.type === "single_choice"
                        ? (selected.options?.find((option) =>
                            option.startsWith(selected.correctOption!),
                          ) ?? "")
                        : selected.referenceAnswer || "暂无参考答案。"}
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-1 text-[11px] leading-5 text-ink-muted">
                {selected.origin === "mine" && (
                  <>
                    <p>
                      最后作答：
                      {selected.lastAttemptAt
                        ? formatDateTime(selected.lastAttemptAt)
                        : "还没有作答记录"}
                    </p>
                    {selected.lastAttemptAt && (
                      <p>已有作答记录，题目暂不可删除。</p>
                    )}
                  </>
                )}
              </div>

              {selected.origin === "mine" && (
                <DialogFooter className="mt-1 border-t border-line pt-4">
                  <Button
                    variant="destructive-outline"
                    size="sm"
                    className="mr-auto h-9 gap-1.5"
                    disabled={Boolean(selected.lastAttemptAt)}
                    title={
                      selected.lastAttemptAt
                        ? "已有作答记录，暂不能删除"
                        : "删除这道题"
                    }
                    onClick={() => setDeleteTarget(selected)}
                  >
                    <Trash2 className="size-3.5" aria-hidden="true" />
                    删除
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-9 gap-1.5"
                    onClick={() => {
                      const target = selected
                      closeDetail()
                      openEditor(target)
                    }}
                  >
                    <Pencil className="size-3.5" aria-hidden="true" />
                    编辑
                  </Button>
                </DialogFooter>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>

      <QuestionEditor
        open={editorOpen}
        question={editing}
        onOpenChange={(open) => {
          setEditorOpen(open)
          if (!open) setEditing(null)
        }}
      />

      <AlertDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除这道私有题？</AlertDialogTitle>
            <AlertDialogDescription>
              删除后无法恢复。已有作答记录的题目不能删除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!deleteTarget) return
                if (deleteTarget.lastAttemptAt) {
                  toast.error("这道题已有作答记录，不能删除")
                  setDeleteTarget(null)
                  return
                }
                deleteQuestion(deleteTarget.id)
                setDeleteTarget(null)
                closeDetail()
                toast("题目已删除")
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
