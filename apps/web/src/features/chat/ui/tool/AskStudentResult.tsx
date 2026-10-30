import { CheckCircle2, ChevronDown } from "lucide-react"
import { useMemo, useState, type ReactNode } from "react"

import { cn } from "@/shared/lib/utils"

import {
  optionLabel,
  parseAskQuestion,
  parseAskResult,
} from "../../model/tool-call"

function AnswerRow({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="flex gap-3 text-[11.5px] leading-5">
      <span className="w-14 shrink-0 text-ink-muted">{label}</span>
      <div className="min-w-0 flex-1 whitespace-pre-wrap text-ink-soft">
        {children}
      </div>
    </div>
  )
}

export function AskStudentResult({
  args,
  result,
}: {
  args: unknown
  result: unknown
}) {
  const [open, setOpen] = useState(true)
  const question = useMemo(() => parseAskQuestion(args), [args])
  const parsed = useMemo(() => parseAskResult(result), [result])
  const isChoice =
    question.mode === "single_choice" ||
    (question.mode !== "short_answer" && question.options.length > 0)
  const student = parsed.student
  const reference = parsed.reference ?? question.referenceAnswer
  const selectedLetter =
    isChoice && student && /^[A-F]$/i.test(student)
      ? student.toUpperCase()
      : undefined
  const correctLetter = (
    question.correctOption ??
    (isChoice && reference && /^[A-F]$/i.test(reference)
      ? reference.toUpperCase()
      : undefined)
  )?.toUpperCase()
  const selectedText =
    optionLabel(selectedLetter, question.options) ?? student ?? "未记录"
  const referenceText =
    optionLabel(correctLetter, question.options) ?? reference ?? "未记录"
  const questionText = question.question ?? "题目未记录"
  const hasOptions = isChoice && question.options.length > 0

  return (
    <div className="w-full overflow-hidden rounded-lg border border-link-line bg-surface-2/70">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 border-b border-line px-4 py-2.5 text-left transition-colors hover:bg-surface-2"
      >
        <CheckCircle2
          className="size-3.5 shrink-0 text-link"
          aria-hidden="true"
        />
        <span className="shrink-0 text-[11px] text-ink-muted">已作答</span>
        <span className="shrink-0 text-[10px] text-ink-muted/70">
          {isChoice ? "单选题" : "简答题"}
        </span>
        {!open && (
          <span className="min-w-0 flex-1 truncate text-[11px] text-ink-muted">
            {questionText}
          </span>
        )}
        <span className="ml-auto shrink-0 text-[10px] text-ink-muted">
          {open ? "收起" : "展开"}
        </span>
        <ChevronDown
          className={cn(
            "size-3.5 shrink-0 text-ink-muted transition-transform",
            open && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div className="px-4 py-3">
          <p className="text-[12.5px] leading-5 whitespace-pre-wrap text-ink-soft">
            {questionText}
          </p>
          {hasOptions ? (
            <div className="mt-3 space-y-1.5 border-t border-line/70 pt-3">
              {question.options.map((option, index) => {
                const letter = String.fromCharCode(65 + index)
                const selected = selectedLetter === letter
                const correct = correctLetter === letter
                return (
                  <div
                    key={`${letter}-${option}`}
                    className={cn(
                      "rounded-md border px-3 py-2 text-[11.5px] leading-5",
                      correct
                        ? "border-link-line bg-link-soft/55"
                        : selected
                          ? "border-danger-line bg-danger-soft/55"
                          : "border-line bg-surface",
                    )}
                  >
                    {selected && (
                      <span className="sr-only">你的选择：</span>
                    )}
                    {correct && (
                      <span className="sr-only">标准答案：</span>
                    )}
                    <span className="block whitespace-pre-wrap text-ink">
                      {option}
                    </span>
                  </div>
                )
              })}
              {!selectedLetter && student && (
                <p className="pt-1 text-[11px] leading-5 text-ink-muted">
                  你的作答：{student}
                </p>
              )}
              {!correctLetter && reference && (
                <p className="pt-1 text-[11px] leading-5 text-ink-muted">
                  参考答案：{reference}
                </p>
              )}
            </div>
          ) : (
            <div className="mt-3 space-y-2 border-t border-line/70 pt-3">
              <AnswerRow label={isChoice ? "你的选择" : "你的作答"}>
                {selectedText}
              </AnswerRow>
              <AnswerRow label={isChoice ? "标准答案" : "参考答案"}>
                {referenceText}
              </AnswerRow>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
