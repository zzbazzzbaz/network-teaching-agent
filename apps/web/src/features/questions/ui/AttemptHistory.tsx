import { ArrowUpRight } from "lucide-react"
import { useNavigate } from "@tanstack/react-router"

import type {
  QuestionAttemptItem,
  QuestionDetail,
  QuestionType,
} from "@/shared/api/types"
import { formatDateTime } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"

import { useQuestionAttempts } from "../queries"

function answerText(
  attempt: QuestionAttemptItem,
  questionType: QuestionType,
  options: string[] | null | undefined,
): string {
  if (questionType !== "single_choice" || !options) {
    return attempt.answer_text
  }
  const index = attempt.answer_text.charCodeAt(0) - 65
  const option = options[index]
  return option ? `${attempt.answer_text} · ${option}` : attempt.answer_text
}

function AttemptRow({
  attempt,
  questionType,
  options,
  onOpen,
}: {
  attempt: QuestionAttemptItem
  questionType: QuestionType
  options: string[] | null | undefined
  onOpen: (attempt: QuestionAttemptItem) => void
}) {
  return (
    <li className="flex items-start gap-3 border-b border-line/70 py-2.5 last:border-b-0">
      <div className="min-w-0 flex-1">
        <p className="text-[10.5px] text-ink-muted">
          {formatDateTime(attempt.created_at)}
        </p>
        <p className="mt-0.5 line-clamp-3 text-[12.5px] leading-5 break-words whitespace-pre-wrap text-ink-soft">
          {answerText(attempt, questionType, options)}
        </p>
      </div>

      {attempt.session_exists && attempt.thread_id ? (
        <button
          type="button"
          onClick={() => onOpen(attempt)}
          aria-label={`打开会话：${attempt.session_title || "未命名会话"}`}
          className="group flex max-w-[42%] shrink-0 items-center gap-1 rounded-sm px-1.5 py-1 text-left text-[11px] text-ink-muted transition-colors hover:bg-surface-2 hover:text-link"
        >
          <span className="truncate">
            {attempt.session_title || "未命名会话"}
          </span>
          <ArrowUpRight
            className="size-3 shrink-0 transition-colors group-hover:text-link"
            aria-hidden="true"
          />
        </button>
      ) : (
        <span className="shrink-0 px-1.5 py-1 text-[11px] text-ink-muted">
          会话已删除
        </span>
      )}
    </li>
  )
}

export function AttemptHistory({
  question,
}: {
  question: QuestionDetail
}) {
  const navigate = useNavigate()
  const mine = question.origin === "mine"
  const attempts = useQuestionAttempts(question.question_id, mine)
  const items = attempts.data?.pages.flatMap((page) => page.items) ?? []
  const total = attempts.data?.pages[0]?.total ?? 0

  function openSession(attempt: QuestionAttemptItem) {
    if (!attempt.thread_id) return
    if (attempt.agent_id === "exp_agent") {
      void navigate({
        to: "/lab/$sessionId",
        params: { sessionId: attempt.thread_id },
      })
    } else {
      void navigate({
        to: "/learn/$sessionId",
        params: { sessionId: attempt.thread_id },
      })
    }
  }

  if (!mine) {
    return (
      <p className="text-[11px] leading-5 text-ink-muted">
        公共题不记录作答；开始学习时，老师会基于题干生成一道私有练习题。
      </p>
    )
  }

  return (
    <section aria-label="作答记录" className="space-y-1">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-medium text-ink-soft">作答记录</h3>
        {attempts.data && total > 0 && (
          <span className="font-mono text-[10px] tabular-nums text-ink-muted">
            {total}
          </span>
        )}
      </div>

      {attempts.isPending ? (
        <div className="space-y-2 py-1" role="status" aria-label="正在加载作答记录">
          {Array.from({ length: 2 }).map((_, index) => (
            <div key={index} className="animate-pulse space-y-1.5">
              <div className="h-2.5 w-24 rounded-sm bg-surface-3" />
              <div className="h-3.5 w-3/4 rounded-sm bg-surface-3" />
            </div>
          ))}
        </div>
      ) : attempts.isError ? (
        <div className="flex items-center gap-2 rounded-md border border-danger-line bg-danger-soft/40 px-3 py-2 text-[11px] text-danger">
          <span>作答记录加载失败。</span>
          <button
            type="button"
            onClick={() => void attempts.refetch()}
            className="font-medium underline underline-offset-2"
          >
            重试
          </button>
        </div>
      ) : items.length === 0 ? (
        <p className="py-1 text-[11px] leading-5 text-ink-muted">
          还没有作答记录。
        </p>
      ) : (
        <>
          <ul>
            {items.map((attempt) => (
              <AttemptRow
                key={attempt.attempt_id}
                attempt={attempt}
                questionType={question.question_type}
                options={question.options}
                onOpen={openSession}
              />
            ))}
          </ul>
          {attempts.hasNextPage && (
            <div className="flex justify-center pt-1">
              <Button
                variant="outline"
                size="sm"
                className="h-9 sm:h-8"
                disabled={attempts.isFetchingNextPage}
                onClick={() => void attempts.fetchNextPage()}
              >
                {attempts.isFetchingNextPage ? "正在加载…" : "加载更多"}
              </Button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
