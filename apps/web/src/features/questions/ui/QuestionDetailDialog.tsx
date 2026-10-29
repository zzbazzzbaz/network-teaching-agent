import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Eye, Lock, Pencil, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import type { QuestionDetail } from "@/shared/api/types"
import { cn, formatDateTime } from "@/shared/lib/utils"
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
import { Badge } from "@/shared/ui/badge"
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
  correctOptionText,
  isNotFoundError,
  optionLetter,
  originLabel,
  questionErrorMessage,
  typeLabel,
} from "../model"
import {
  questionDetailQueryOptions,
  questionKeys,
  useDeleteQuestion,
} from "../queries"

function answerText(question: QuestionDetail): string {
  if (question.question_type === "single_choice") {
    return correctOptionText(question) ?? "暂无正确答案。"
  }
  return question.reference_answer?.trim() || "暂无参考答案。"
}

export function QuestionDetailDialog({
  questionId,
  onClose,
  onEdit,
}: {
  questionId: string
  onClose: () => void
  onEdit: (question: QuestionDetail) => void
}) {
  const detailQuery = useQuery(questionDetailQueryOptions(questionId))
  const queryClient = useQueryClient()
  const removeQuestion = useDeleteQuestion()
  const [revealed, setRevealed] = useState(false)
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)

  useEffect(() => {
    setRevealed(false)
  }, [questionId])

  useEffect(() => {
    if (!isNotFoundError(detailQuery.error)) return
    // 详情已不存在时，顺手让列表和计数重新拉取。
    void queryClient.invalidateQueries({ queryKey: questionKeys.lists() })
    void queryClient.invalidateQueries({ queryKey: questionKeys.counts() })
  }, [detailQuery.error, queryClient])

  const question = detailQuery.data

  async function handleDelete() {
    if (!question) return
    try {
      await removeQuestion.mutateAsync(question.question_id)
      setConfirmDeleteOpen(false)
      toast("题目已删除")
      onClose()
    } catch (error) {
      setConfirmDeleteOpen(false)
      toast.error(questionErrorMessage(error, "删除失败，请稍后重试。"))
      if (isNotFoundError(error)) {
        onClose()
      } else {
        void detailQuery.refetch()
      }
    }
  }

  return (
    <>
      <Dialog
        open
        onOpenChange={(open) => {
          if (!open) onClose()
        }}
      >
        <DialogContent className="max-w-2xl">
          {detailQuery.isPending && <DetailLoading />}

          {detailQuery.isError && (
            <DetailError
              error={detailQuery.error}
              onClose={onClose}
              onRetry={() => void detailQuery.refetch()}
            />
          )}

          {question && (
            <>
              <DialogHeader>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="muted">
                    {typeLabel(question.question_type)}
                  </Badge>
                  <Badge
                    variant={
                      question.origin === "public" ? "outline" : "default"
                    }
                  >
                    {originLabel(question.origin)}
                  </Badge>
                  <span className="max-w-full truncate text-[11px] text-ink-muted">
                    {question.primary_knowledge_point.title}
                  </span>
                </div>
                <DialogTitle className="mt-1.5 pr-5 text-[15px] leading-7 font-medium">
                  {question.stem}
                </DialogTitle>
                <DialogDescription className="sr-only">
                  题目详情与答案
                </DialogDescription>
              </DialogHeader>

              {question.question_type === "single_choice" &&
                question.options && (
                  <ol className="mt-1 space-y-2">
                    {question.options.map((option, index) => {
                      const letter = optionLetter(index)
                      const isCorrect =
                        revealed && question.correct_option === letter
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
                          <span className="min-w-0 break-words">{option}</span>
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
                      onClick={() => setRevealed(true)}
                    >
                      <Eye className="size-3.5" aria-hidden="true" />
                      查看答案
                    </Button>
                  </div>
                ) : (
                  <div className="rounded-md border border-link-line bg-link-soft/50 px-3 py-3">
                    <div className="flex items-center gap-1.5 text-[11px] font-medium text-link-strong">
                      <Check className="size-3.5" aria-hidden="true" />
                      {question.question_type === "single_choice"
                        ? `正确答案：${question.correct_option ?? "未设置"}`
                        : "参考答案"}
                    </div>
                    <p className="mt-1.5 text-[12.5px] leading-6 break-words whitespace-pre-wrap text-ink-soft">
                      {answerText(question)}
                    </p>
                  </div>
                )}
              </div>

              {question.origin === "mine" ? (
                <div className="space-y-1 text-[11px] leading-5 text-ink-muted">
                  <p>
                    最后作答：
                    {question.last_attempt_at
                      ? formatDateTime(question.last_attempt_at)
                      : "还没有作答记录"}
                  </p>
                </div>
              ) : (
                <p className="text-[11px] leading-5 text-ink-muted">
                  公共题由老师维护，只能查看。
                </p>
              )}

              <DialogFooter className="mt-1 border-t border-line pt-4">
                {question.origin === "mine" ? (
                  <>
                    <DeleteButton
                      pending={removeQuestion.isPending}
                      onDelete={() => setConfirmDeleteOpen(true)}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-10 gap-1.5 sm:h-9"
                      onClick={() => onEdit(question)}
                    >
                      <Pencil className="size-3.5" aria-hidden="true" />
                      编辑
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-10 sm:h-9"
                    onClick={onClose}
                  >
                    关闭
                  </Button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={confirmDeleteOpen}
        onOpenChange={(open) => {
          if (!removeQuestion.isPending) setConfirmDeleteOpen(open)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除这道私有题？</AlertDialogTitle>
            <AlertDialogDescription>
              删除后题目将从题库中移除，历史作答记录会保留。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              className="h-11 sm:h-9"
              disabled={removeQuestion.isPending}
            >
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              className="h-11 sm:h-9"
              disabled={removeQuestion.isPending}
              onClick={(event) => {
                event.preventDefault()
                void handleDelete()
              }}
            >
              {removeQuestion.isPending ? "正在删除…" : "删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

function DeleteButton({
  pending,
  onDelete,
}: {
  pending: boolean
  onDelete: () => void
}) {
  return (
    <Button
      variant="destructive-outline"
      size="sm"
      className="mr-auto h-10 gap-1.5 sm:h-9"
      disabled={pending}
      onClick={onDelete}
    >
      <Trash2 className="size-3.5" aria-hidden="true" />
      删除
    </Button>
  )
}

function DetailLoading() {
  return (
    <>
      <DialogHeader>
        <DialogTitle className="text-[15px] font-medium">题目详情</DialogTitle>
        <DialogDescription>正在加载题目内容…</DialogDescription>
      </DialogHeader>
      <div
        className="animate-pulse space-y-2"
        role="status"
        aria-label="正在加载题目详情"
      >
        <div className="h-3.5 w-4/5 rounded-sm bg-surface-3" />
        <div className="h-3.5 w-2/3 rounded-sm bg-surface-3" />
        <div className="mt-4 space-y-2">
          <div className="h-10 rounded-md bg-surface-2" />
          <div className="h-10 rounded-md bg-surface-2" />
          <div className="h-10 rounded-md bg-surface-2" />
        </div>
        <div className="mt-4 h-16 rounded-md bg-surface-2" />
      </div>
    </>
  )
}

function DetailError({
  error,
  onClose,
  onRetry,
}: {
  error: unknown
  onClose: () => void
  onRetry: () => void
}) {
  const notFound = isNotFoundError(error)
  const message = notFound
    ? "这道题不存在，可能已经被删除。"
    : questionErrorMessage(error, "题目加载失败，请稍后重试。")

  return (
    <>
      <DialogHeader>
        <DialogTitle className="text-[15px] font-medium">题目详情</DialogTitle>
        <DialogDescription className="sr-only">
          题目详情加载失败
        </DialogDescription>
      </DialogHeader>
      <div
        role="alert"
        className="rounded-md border border-line bg-surface-2 px-4 py-8 text-center"
      >
        <p className="text-[12.5px] leading-6 text-ink-soft">{message}</p>
        <div className="mt-4 flex justify-center gap-2">
          {!notFound && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              重试
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onClose}>
            关闭
          </Button>
        </div>
      </div>
    </>
  )
}
