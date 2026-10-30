import { Pencil, Trash2 } from "lucide-react"
import { useMemo, useState } from "react"
import { z } from "zod"

import { useKnowledgePoints } from "@/features/course"
import {
  LETTERS,
  typeLabel,
  validateQuestionDraft,
  type QuestionEditorDraft,
} from "@/features/questions/model"
import { QuestionEditorDialog } from "@/features/questions/ui/QuestionEditorDialog"
import type {
  QuestionDetail,
  QuestionInput,
} from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"

import type { ChatStream } from "../model/useChatSession"

const draftSchema = z.object({
  mode: z.enum(["single_choice", "short_answer"]),
  stem: z.string().min(1).max(4000),
  options: z.array(z.string()).nullable().optional(),
  correct_option: z.string().nullable().optional(),
  reference_answer: z.string().nullable().optional(),
  primary_knowledge_point_id: z.string().min(1).max(16),
  secondary_knowledge_point_ids: z.array(z.string()).max(3).default([]),
})

const payloadSchema = z.object({
  type: z.literal("question_import"),
  questions: z.array(draftSchema).min(1).max(5),
})

type ImportDraft = z.infer<typeof draftSchema>

function parsePayload(value: unknown): ImportDraft[] | undefined {
  const parsed = payloadSchema.safeParse(value)
  return parsed.success ? parsed.data.questions : undefined
}

function toEditorDraft(draft: ImportDraft): QuestionEditorDraft {
  const choice = draft.mode === "single_choice"
  const optionTexts = choice ? (draft.options ?? []) : []
  const correctIndex =
    choice && draft.correct_option
      ? LETTERS.findIndex((letter) => letter === draft.correct_option)
      : -1
  return {
    questionType: draft.mode,
    stem: draft.stem,
    optionTexts,
    correctIndex,
    referenceAnswer: choice ? "" : (draft.reference_answer ?? ""),
    primaryKnowledgePointId: draft.primary_knowledge_point_id,
    secondaryKnowledgePointIds:
      draft.secondary_knowledge_point_ids ?? [],
  }
}

function fromQuestionInput(input: QuestionInput): ImportDraft {
  return {
    mode: input.question_type,
    stem: input.stem,
    options: input.options ?? null,
    correct_option: input.correct_option ?? null,
    reference_answer: input.reference_answer ?? null,
    primary_knowledge_point_id: input.primary_knowledge_point_id,
    secondary_knowledge_point_ids:
      input.secondary_knowledge_point_ids ?? [],
  }
}

function toAgentQuestion(input: QuestionInput) {
  return {
    mode: input.question_type,
    stem: input.stem,
    options: input.options ?? null,
    correct_option: input.correct_option ?? null,
    reference_answer: input.reference_answer ?? null,
    primary_knowledge_point_id: input.primary_knowledge_point_id,
    secondary_knowledge_point_ids:
      input.secondary_knowledge_point_ids ?? [],
  }
}

function firstError(errors: Record<string, string | undefined>): string {
  return (
    Object.values(errors).find((value): value is string => Boolean(value)) ??
    "请检查题目内容。"
  )
}

function DraftSummary({
  draft,
  index,
  invalidMessage,
  canRemove,
  onEdit,
  onRemove,
}: {
  draft: ImportDraft
  index: number
  invalidMessage: string | null
  canRemove: boolean
  onEdit: () => void
  onRemove: () => void
}) {
  const choice = draft.mode === "single_choice"
  return (
    <li className="px-4 py-3">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="muted">{typeLabel(draft.mode)}</Badge>
            <span className="font-mono text-[10px] text-ink-muted">
              {draft.primary_knowledge_point_id}
            </span>
          </div>

          <p className="mt-1.5 line-clamp-3 text-[13px] leading-6 break-words whitespace-pre-wrap text-ink">
            {draft.stem}
          </p>

          {choice && draft.options && draft.options.length > 0 && (
            <ul className="mt-2 space-y-1">
              {draft.options.map((option, optionIndex) => {
                const letter = LETTERS[optionIndex]
                const correct = draft.correct_option === letter
                return (
                  <li
                    key={`${letter}-${option}`}
                    className={cn(
                      "text-[11.5px] leading-5 break-words",
                      correct ? "text-link-strong" : "text-ink-muted",
                    )}
                  >
                    {letter}. {option}
                    {correct && (
                      <span className="ml-1.5 text-[10px]">答案</span>
                    )}
                  </li>
                )
              })}
            </ul>
          )}

          {!choice && (
            <p className="mt-1.5 line-clamp-2 text-[11.5px] leading-5 text-ink-muted">
              参考答案：{draft.reference_answer?.trim() || "未填写"}
            </p>
          )}

          {invalidMessage && (
            <p role="alert" className="mt-1.5 text-[11px] text-danger">
              {invalidMessage}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-0.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-9 gap-1 px-2 sm:h-8"
            onClick={onEdit}
            aria-label={`编辑第 ${index + 1} 道题`}
          >
            <Pencil className="size-3.5" aria-hidden="true" />
            编辑
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            className="text-ink-muted hover:text-danger"
            disabled={!canRemove}
            onClick={onRemove}
            aria-label={`删除第 ${index + 1} 道题`}
            title={canRemove ? "删除这道题" : "至少保留一道；取消请点「取消」"}
          >
            <Trash2 className="size-3.5" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </li>
  )
}

export function QuestionImportCard({
  interrupt,
  stream,
}: {
  interrupt: { id?: string; value?: unknown }
  stream: ChatStream
}) {
  const payload = parsePayload(interrupt.value)
  const [drafts, setDrafts] = useState<ImportDraft[]>(() => payload ?? [])
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submittedLabel, setSubmittedLabel] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const knowledgePointsQuery = useKnowledgePoints()
  const titleById = useMemo(
    () =>
      new Map(
        (knowledgePointsQuery.data?.nodes ?? []).map((node) => [
          node.id,
          node.title,
        ]),
      ),
    [knowledgePointsQuery.data],
  )

  if (!payload || drafts.length === 0) {
    return (
      <section className="w-full overflow-hidden rounded-lg border border-line bg-surface">
        <div className="border-b border-line px-4 py-2">
          <span className="text-[11px] font-medium text-signal">导入题目</span>
        </div>
        <p className="px-4 py-3 text-[11.5px] leading-5 text-ink-muted">
          题目数据格式异常，暂时无法确认。可以请老师重新解析一次。
        </p>
        <pre className="scroll-slim max-h-52 overflow-auto border-t border-line px-4 py-3 font-mono text-[10.5px] leading-5 text-ink-soft">
          {JSON.stringify(interrupt.value, null, 2)}
        </pre>
      </section>
    )
  }

  const validations = drafts.map((draft) =>
    validateQuestionDraft(toEditorDraft(draft)),
  )
  const firstInvalidIndex = validations.findIndex(
    (validation) => !validation.payload,
  )
  const invalid = firstInvalidIndex >= 0

  const editingDraft = editingIndex === null ? null : drafts[editingIndex]

  function toDetail(draft: ImportDraft): QuestionDetail {
    const choice = draft.mode === "single_choice"
    return {
      question_id: `import-${editingIndex ?? 0}`,
      origin: "mine",
      question_type: draft.mode,
      stem: draft.stem,
      options: choice ? (draft.options ?? []) : null,
      correct_option: choice ? (draft.correct_option ?? null) : null,
      reference_answer: choice
        ? null
        : (draft.reference_answer ?? null),
      primary_knowledge_point: {
        id: draft.primary_knowledge_point_id,
        title:
          titleById.get(draft.primary_knowledge_point_id) ??
          draft.primary_knowledge_point_id,
      },
      secondary_knowledge_points: draft.secondary_knowledge_point_ids.map(
        (id) => ({ id, title: titleById.get(id) ?? id }),
      ),
      last_attempt_at: null,
    }
  }

  function removeDraft(index: number) {
    setDrafts((previous) => previous.filter((_, itemIndex) => itemIndex !== index))
    if (editingIndex === index) setEditingIndex(null)
  }

  async function submit() {
    if (submitting || submittedLabel || invalid) return
    const questions = validations
      .map((validation) => validation.payload)
      .filter((item): item is QuestionInput => item !== null)
      .map(toAgentQuestion)
    if (questions.length === 0) return

    setSubmitting(true)
    setError(null)
    try {
      await stream.respond(
        { action: "save", questions },
        interrupt.id ? { interruptId: interrupt.id } : {},
      )
      setSubmittedLabel("已提交，等待老师确认…")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setSubmitting(false)
    }
  }

  async function cancel() {
    if (submitting || submittedLabel) return
    setSubmitting(true)
    setError(null)
    try {
      await stream.respond(
        { action: "cancel", questions: [] },
        interrupt.id ? { interruptId: interrupt.id } : {},
      )
      setSubmittedLabel("已取消，等待老师继续…")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <section className="w-full overflow-hidden rounded-lg border border-line bg-surface">
        <header className="border-b border-line px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-medium text-signal">导入题目</span>
            <Badge variant="muted">{drafts.length} 道</Badge>
          </div>
          <p className="mt-1 text-[11.5px] leading-5 text-ink-muted">
            老师解析出的题目。确认后保存到「我的题库」，不会发布公共题。
          </p>
        </header>

        <ol className="divide-y divide-line/70">
          {drafts.map((draft, index) => (
            <DraftSummary
              key={`${index}-${draft.stem}`}
              draft={draft}
              index={index}
              invalidMessage={
                validations[index]?.payload
                  ? null
                  : firstError(validations[index]?.errors ?? {})
              }
              canRemove={drafts.length > 1}
              onEdit={() => setEditingIndex(index)}
              onRemove={() => removeDraft(index)}
            />
          ))}
        </ol>

        {invalid && (
          <p
            role="alert"
            className="border-t border-line px-4 py-2 text-[11.5px] leading-5 text-danger"
          >
            第 {firstInvalidIndex + 1} 道还需要完善。点「编辑」补上正确答案或知识点后再保存。
          </p>
        )}

        {error && (
          <p
            role="alert"
            className="border-t border-line px-4 py-2 text-[11.5px] leading-5 text-danger"
          >
            {error}
          </p>
        )}

        {submittedLabel ? (
          <div className="border-t border-line px-4 py-3 text-[11.5px] text-link">
            {submittedLabel}
          </div>
        ) : (
          <footer className="flex items-center justify-end gap-2 border-t border-line px-4 py-3">
            <Button
              type="button"
              variant="ghost"
              className="h-10 sm:h-9"
              disabled={submitting}
              onClick={() => void cancel()}
            >
              取消
            </Button>
            <Button
              type="button"
              className="h-10 sm:h-9"
              disabled={submitting || invalid}
              onClick={() => void submit()}
            >
              {submitting ? "正在保存…" : "保存到我的题库"}
            </Button>
          </footer>
        )}
      </section>

      {editingDraft && editingIndex !== null && (
        <QuestionEditorDialog
          key={`import-${editingIndex}`}
          question={toDetail(editingDraft)}
          onClose={() => setEditingIndex(null)}
          onSaved={() => undefined}
          initialCorrectOption={editingDraft.correct_option ?? null}
          onSubmit={(input) => {
            setDrafts((previous) =>
              previous.map((draft, index) =>
                index === editingIndex
                  ? fromQuestionInput(input)
                  : draft,
              ),
            )
          }}
        />
      )}
    </>
  )
}
