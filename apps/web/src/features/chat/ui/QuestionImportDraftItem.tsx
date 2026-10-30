import { Pencil, Trash2 } from "lucide-react"

import { LETTERS, typeLabel } from "@/features/questions/model"
import { cn } from "@/shared/lib/utils"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"

import type { ImportDraft } from "../model/question-import"

export function QuestionImportDraftItem({
  draft,
  index,
  invalidMessage,
  canRemove,
  disabled = false,
  onEdit,
  onRemove,
}: {
  draft: ImportDraft
  index: number
  invalidMessage: string | null
  canRemove: boolean
  disabled?: boolean
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
            disabled={disabled}
            aria-label={`编辑第 ${index + 1} 道题`}
          >
            <Pencil className="size-3.5" aria-hidden="true" />
            编辑
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            className="text-ink-muted hover:text-danger"
            disabled={!canRemove || disabled}
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
