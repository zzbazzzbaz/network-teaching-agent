import { CheckCircle2, ChevronDown, Loader2 } from "lucide-react"
import { useId, useState } from "react"
import { z } from "zod"

import { Button } from "@/shared/ui/button"
import { RadioGroup, RadioGroupItem } from "@/shared/ui/radio-group"
import { cn } from "@/shared/lib/utils"

import type { ChatStream } from "../model/useChatSession"

const answerSchema = z
  .object({
    correct_option: z.string().optional(),
    reference_answer: z.string().optional(),
  })
  .optional()

const askStudentSchema = z.union([
  z.object({
    type: z.literal("ask_student"),
    mode: z.literal("single_choice"),
    question: z.string().min(1),
    options: z.array(z.string()).min(2).max(6),
    placeholder: z.string().optional(),
    answer: answerSchema,
  }),
  z.object({
    type: z.literal("ask_student"),
    mode: z.literal("short_answer"),
    question: z.string().min(1),
    options: z.null().optional(),
    placeholder: z.string().optional(),
    answer: answerSchema,
  }),
])

type AskStudentPayload = z.infer<typeof askStudentSchema>

function parsePayload(value: unknown): AskStudentPayload | undefined {
  const parsed = askStudentSchema.safeParse(value)
  return parsed.success ? parsed.data : undefined
}

function optionLetter(index: number): string {
  return String.fromCharCode(65 + index)
}

/** 即使 payload 不合法，也不在作答前把答案渲染出来。 */
function safeInterruptPayload(value: unknown): unknown {
  if (!value || typeof value !== "object") return value
  const record = value as Record<string, unknown>
  if (record.type !== "ask_student") return value
  return { ...record, answer: "[hidden until submitted]" }
}

export function AskStudentCard({
  interrupt,
  stream,
}: {
  interrupt: { id?: string; value?: unknown }
  stream: ChatStream
}) {
  const uid = useId()
  const [selected, setSelected] = useState("")
  const [answer, setAnswer] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [open, setOpen] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const payload = parsePayload(interrupt.value)

  if (!payload) {
    return (
      <section className="w-full overflow-hidden rounded-lg border border-signal-line bg-signal-soft/30">
        <div className="flex items-center gap-2 border-b border-signal-line/60 px-4 py-2">
          <span className="size-1.5 rounded-full bg-signal" aria-hidden="true" />
          <span className="text-[11px] font-medium text-signal">Agent 暂停</span>
        </div>
        <p className="border-b border-signal-line/40 px-4 py-2 text-[11.5px] text-ink-muted">
          题目数据格式异常，暂时无法作答。
        </p>
        <pre className="scroll-slim max-h-56 overflow-auto px-4 py-3 font-mono text-[10.5px] leading-5 text-ink-soft">
          {JSON.stringify(safeInterruptPayload(interrupt.value), null, 2)}
        </pre>
      </section>
    )
  }

  async function respond(value: string) {
    if (submitting || submitted) return
    setSubmitting(true)
    setError(null)
    try {
      const responseOptions = interrupt.id ? { interruptId: interrupt.id } : {}
      await stream.respond({ answer: value }, responseOptions)
      setSubmitted(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setSubmitting(false)
    }
  }

  function submitChoice() {
    if (!selected) return
    void respond(selected)
  }

  function submitAnswer() {
    const trimmed = answer.trim()
    if (!trimmed) return
    void respond(trimmed)
  }

  return (
    <section
      className="w-full overflow-hidden rounded-lg border border-signal-line bg-signal-soft/35 text-left"
      aria-label="作答检查点"
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={`${uid}-body`}
        className="flex w-full items-center gap-2 border-b border-signal-line/60 px-4 py-2 text-left transition-colors hover:bg-signal-soft/35"
      >
        <span className="size-1.5 shrink-0 rounded-full bg-signal" aria-hidden="true" />
        <span className="shrink-0 text-[11px] font-medium text-signal">作答检查点</span>
        {!open && (
          <span className="min-w-0 flex-1 truncate text-[11px] text-ink-muted">
            {payload.question}
          </span>
        )}
        <span className="ml-auto shrink-0 text-[10px] text-signal/60">
          {open ? "收起" : "展开"}
        </span>
        <ChevronDown
          className={cn(
            "size-3.5 shrink-0 text-signal/70 transition-transform",
            open && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div id={`${uid}-body`}>
          <div className="px-4 pt-3.5 pb-1">
            <p className="text-[14px] leading-6 font-medium text-ink">
              {payload.question}
            </p>
          </div>

          {payload.mode === "single_choice" ? (
        <>
          <RadioGroup
            value={selected}
            onValueChange={setSelected}
            aria-label={payload.question}
            className="mt-2 gap-0 border-t border-signal-line/40"
            disabled={submitting || submitted}
          >
            {payload.options.map((option, index) => {
              const letter = optionLetter(index)
              const id = `${uid}-${index}`
              return (
                <label
                  key={`${letter}-${option}`}
                  htmlFor={id}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 border-b border-signal-line/40 px-4 py-3 transition-colors last:border-b-0",
                    "hover:bg-signal-soft/50 has-[[data-state=checked]]:bg-signal-soft/60",
                    (submitting || submitted) && "cursor-default",
                  )}
                >
                  <RadioGroupItem
                    id={id}
                    value={letter}
                    className="mt-0.5 border-signal/45 data-[state=checked]:border-signal data-[state=checked]:bg-signal"
                  />
                  <span className="min-w-0 text-[13px] leading-5 text-ink">
                    <span className="sr-only">选项 {letter}：</span>
                    {option}
                  </span>
                </label>
              )
            })}
          </RadioGroup>

          <div className="flex items-center justify-end gap-3 border-t border-signal-line/50 px-4 py-3">
            <Button
              type="button"
              disabled={!selected || submitting || submitted}
              onClick={submitChoice}
              className="h-11 shrink-0 gap-1.5 bg-signal px-4 text-white hover:bg-[#7d4700] focus-visible:ring-signal/30 sm:h-10"
            >
              {submitting && (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              )}
              {submitted ? "已提交" : "提交作答"}
            </Button>
          </div>
        </>
      ) : (
        <form
          className="mt-2 border-t border-signal-line/40"
          onSubmit={(event) => {
            event.preventDefault()
            submitAnswer()
          }}
        >
          <textarea
            aria-label="简答题答案"
            placeholder={payload.placeholder || "输入你的答案"}
            value={answer}
            maxLength={2000}
            rows={3}
            disabled={submitting || submitted}
            onChange={(event) => setAnswer(event.target.value)}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                event.preventDefault()
                submitAnswer()
              }
            }}
            className="block min-h-24 w-full resize-y bg-transparent px-4 py-3 text-[16px] leading-6 text-ink outline-none placeholder:text-ink-muted/70 lg:text-[14px]"
          />
          <div className="flex items-center justify-end gap-3 border-t border-signal-line/50 px-4 py-3">
            <Button
              type="submit"
              disabled={!answer.trim() || submitting || submitted}
              className="h-11 shrink-0 gap-1.5 bg-signal px-4 text-white hover:bg-[#7d4700] focus-visible:ring-signal/30 sm:h-10"
            >
              {submitting && (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              )}
              {submitted ? "已提交" : "提交答案"}
            </Button>
          </div>
        </form>
          )}
        </div>
      )}

      {submitted && (
        <div className="flex items-center gap-1.5 border-t border-signal-line/50 px-4 py-2 text-[11px] text-link">
          <CheckCircle2 className="size-3.5" aria-hidden="true" />
          {payload.mode === "single_choice"
            ? `已提交 ${selected}，等待老师继续…`
            : "已提交，等待老师继续…"}
        </div>
      )}
      {error && (
        <p role="alert" className="border-t border-danger-line px-4 py-2 text-[11.5px] text-danger">
          {error}
        </p>
      )}
    </section>
  )
}
