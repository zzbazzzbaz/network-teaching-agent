import { Clock, Eye } from "lucide-react"

import type { QuestionSummary } from "@/shared/api/types"
import { formatDate } from "@/shared/lib/utils"

export function QuestionCard({
  question,
  onOpen,
}: {
  question: QuestionSummary
  onOpen: (questionId: string) => void
}) {
  const lastAttemptAt = question.last_attempt_at

  return (
    <button
      type="button"
      onClick={() => onOpen(question.question_id)}
      className="group flex min-h-[160px] w-full flex-col rounded-lg border border-line bg-surface p-4 text-left transition-colors outline-none hover:border-link-line focus-visible:ring-2 focus-visible:ring-ring/30"
    >
      <div className="mb-2 flex min-w-0 items-center gap-1.5 text-[10.5px] text-ink-muted">
        <span className="shrink-0 font-mono text-[10px] tabular-nums">
          {question.primary_knowledge_point.id}
        </span>
        <span
          className="truncate"
          title={question.primary_knowledge_point.title}
        >
          {question.primary_knowledge_point.title}
        </span>
      </div>
      <p className="line-clamp-3 text-[13.5px] leading-6 break-words text-ink">
        {question.stem_preview}
      </p>

      <div className="mt-auto flex items-center gap-1.5 pt-4 text-[10.5px] text-ink-muted">
        {question.origin === "mine" && (
          <>
            <Clock className="size-3 shrink-0" aria-hidden="true" />
            <span className="truncate">
              {lastAttemptAt
                ? `上次作答 ${formatDate(lastAttemptAt)}`
                : "还没有作答记录"}
            </span>
          </>
        )}
        <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-ink-muted transition-colors group-hover:text-link">
          查看
          <Eye className="size-3" aria-hidden="true" />
        </span>
      </div>
    </button>
  )
}
