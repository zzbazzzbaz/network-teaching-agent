import { useMemo, useState } from "react"

import { useKnowledgePoints } from "@/features/course"
import { QuestionEditorDialog } from "@/features/questions/ui/QuestionEditorDialog"
import type { QuestionDetail, QuestionInput } from "@/shared/api/types"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"

import {
  firstError,
  fromQuestionInput,
  parseImportPayload,
  toAgentQuestion,
  validateImports,
  type ImportDraft,
} from "../model/question-import"
import type { ChatStream } from "../model/useChatSession"
import { QuestionImportDraftItem } from "./QuestionImportDraftItem"

export function QuestionImportCard({
  interrupt,
  stream,
}: {
  interrupt: { id?: string; value?: unknown }
  stream: ChatStream
}) {
  const payload = useMemo(
    () => parseImportPayload(interrupt.value),
    [interrupt.value],
  )
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

  const validations = useMemo(() => validateImports(drafts), [drafts])

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
    setDrafts((previous) =>
      previous.filter((_, itemIndex) => itemIndex !== index),
    )
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
            <QuestionImportDraftItem
              key={`${index}-${draft.stem}`}
              draft={draft}
              index={index}
              invalidMessage={
                validations[index]?.payload
                  ? null
                  : firstError(validations[index]?.errors ?? {})
              }
              canRemove={drafts.length > 1}
              disabled={Boolean(submittedLabel)}
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
