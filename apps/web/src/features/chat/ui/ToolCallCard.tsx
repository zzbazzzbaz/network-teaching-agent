import {
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  FileText,
  Search,
  Terminal,
  Cloud,
  Wrench,
} from "lucide-react"
import { useState, type ReactNode } from "react"
import type {
  ToolCallMessagePartComponent,
  ToolCallMessagePartProps,
} from "@assistant-ui/react"

import { cn } from "@/shared/lib/utils"

function pretty(value: unknown): string {
  if (value === undefined || value === null) return ""
  if (typeof value === "string") return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function truncate(value: string, max = 12_000): string {
  return value.length > max ? `${value.slice(0, max)}\n…（已截断）` : value
}

function argString(args: unknown, keys: string[]): string | undefined {
  if (!args || typeof args !== "object") return undefined
  const record = args as Record<string, unknown>
  for (const key of keys) {
    if (typeof record[key] === "string" && record[key]) return record[key]
  }
  return undefined
}

function iconFor(toolName: string) {
  if (toolName.includes("question")) return Search
  if (toolName.includes("execute") || toolName.includes("terminal")) return Terminal
  if (toolName.includes("sandbox")) return Cloud
  if (toolName.includes("file") || toolName.includes("read") || toolName.includes("write")) {
    return FileText
  }
  if (toolName === "task") return CircleHelp
  return Wrench
}

function summaryFor(toolName: string, args: unknown): string {
  if (toolName === "execute") {
    return argString(args, ["command", "cmd"]) ?? "执行命令"
  }
  if (toolName.includes("search")) return "检索题库"
  if (toolName.includes("save")) return "保存到我的题库"
  if (toolName.includes("sandbox")) return "确认实验沙盒"
  if (toolName === "task") return "分派子任务"
  if (toolName.includes("read")) return argString(args, ["path", "file_path"]) ?? "读取文件"
  if (toolName.includes("write")) return argString(args, ["path", "file_path"]) ?? "写入文件"
  return "工具调用"
}

function statusLabel(status: ToolCallMessagePartProps["status"], isError?: boolean) {
  if (isError) return "失败"
  if (status.type === "running") return "运行中"
  if (status.type === "complete") return "完成"
  if (status.type === "requires-action") return "等待作答"
  return "未完成"
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined
}

function asText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined
}

type AskQuestionData = {
  mode?: "single_choice" | "short_answer"
  question?: string
  options: string[]
  correctOption?: string
  referenceAnswer?: string
}

/** ask_student 的参数既有早期的扁平结构，也有现在嵌套的 question 对象。 */
function parseAskQuestion(args: unknown): AskQuestionData {
  const root = asRecord(args) ?? {}
  const nested = asRecord(root.question)
  const source = nested ?? root
  const rawMode = asText(source.mode) ?? asText(root.mode)
  const optionsValue = Array.isArray(source.options)
    ? source.options
    : Array.isArray(root.options)
      ? root.options
      : []

  return {
    mode:
      rawMode === "single_choice" || rawMode === "short_answer"
        ? rawMode
        : undefined,
    question:
      asText(source.stem) ??
      asText(source.question) ??
      asText(root.question),
    options: optionsValue.filter((value): value is string => typeof value === "string"),
    correctOption: asText(source.correct_option)?.toUpperCase(),
    referenceAnswer: asText(source.reference_answer),
  }
}

function parseAskResult(value: unknown): {
  student?: string
  reference?: string
} {
  const text = pretty(value)
  return {
    student: /学生答案[：:]\s*([\s\S]*?)(?=\n参考答案[：:]|\n（题库记录失败|$)/.exec(
      text,
    )?.[1]?.trim(),
    reference: /参考答案[：:]\s*([\s\S]*?)(?=\n（题库记录失败|$)/.exec(
      text,
    )?.[1]?.trim(),
  }
}

function optionLabel(
  letter: string | undefined,
  options: string[],
): string | undefined {
  if (!letter) return undefined
  const index = letter.charCodeAt(0) - 65
  if (index < 0 || index >= options.length) return letter
  const option = options[index].trim()
  return new RegExp(`^${letter}[.、\\s]`, "i").test(option)
    ? option
    : `${letter}. ${option}`
}

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

function AskStudentResult({
  args,
  result,
}: {
  args: unknown
  result: unknown
}) {
  const [open, setOpen] = useState(true)
  const question = parseAskQuestion(args)
  const parsed = parseAskResult(result)
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
    optionLabel(correctLetter, question.options) ??
    reference ??
    "未记录"
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
        <CheckCircle2 className="size-3.5 shrink-0 text-link" aria-hidden="true" />
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
          <p className="whitespace-pre-wrap text-[12.5px] leading-5 text-ink-soft">
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
                    {selected && <span className="sr-only">你的选择：</span>}
                    {correct && <span className="sr-only">标准答案：</span>}
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

export const ToolCallCard: ToolCallMessagePartComponent = ({
  toolName,
  args,
  result,
  status,
  isError,
}) => {
  const [open, setOpen] = useState(false)

  if (toolName === "ask_student") {
    if (status.type === "running" || status.type === "requires-action") {
      return null
    }
    if (isError) return null
    return <AskStudentResult args={args} result={result} />
  }

  const Icon = iconFor(toolName)
  const command = argString(args, ["command", "cmd"])
  const output = pretty(result)
  const argsText = pretty(args)
  const hasDetail = Boolean(command || output || argsText)
  const summary = summaryFor(toolName, args)
  const complete = status.type === "complete" && !isError

  return (
    <div className="w-full overflow-hidden rounded-md border border-line bg-surface-2/60">
      <button
        type="button"
        onClick={() => hasDetail && setOpen((value) => !value)}
        aria-expanded={hasDetail ? open : undefined}
        disabled={!hasDetail}
        className={cn(
          "flex w-full items-center gap-2 px-3 py-2 text-left",
          hasDetail && "transition-colors hover:bg-surface-2",
          !hasDetail && "cursor-default",
        )}
      >
        <Icon className="size-3.5 shrink-0 text-ink-muted" aria-hidden="true" />
        <span className="shrink-0 font-mono text-[11px] text-ink-soft">
          {toolName}
        </span>
        <span className="min-w-0 flex-1 truncate text-[11.5px] text-ink-muted">
          {summary}
        </span>
        <span
          className={cn(
            "size-1.5 shrink-0 rounded-full",
            complete && "bg-link",
            status.type === "running" && "bg-signal link-pulse",
            isError && "bg-danger",
            !complete && status.type !== "running" && !isError && "bg-line-strong",
          )}
          aria-hidden="true"
        />
        <span className="sr-only">{statusLabel(status, isError)}</span>
        <span
          className={cn(
            "hidden shrink-0 font-mono text-[9.5px] sm:block",
            isError ? "text-danger" : "text-ink-muted",
          )}
        >
          {statusLabel(status, isError)}
        </span>
        {hasDetail && (
          <ChevronDown
            className={cn(
              "size-3.5 shrink-0 text-ink-muted transition-transform",
              open && "rotate-180",
            )}
            aria-hidden="true"
          />
        )}
      </button>

      {hasDetail && open && (
        <div className="border-t border-line bg-surface">
          {command && (
            <div className="border-b border-line px-3 py-2">
              <span className="font-mono text-[11px] text-ink-muted select-none">
                ${" "}
              </span>
              <span className="font-mono text-[11px] break-all text-ink-soft">
                {command}
              </span>
            </div>
          )}

          {output && (
            <pre className="scroll-slim max-h-[260px] overflow-auto px-3 py-2.5 font-mono text-[10.5px] leading-[1.75] whitespace-pre-wrap text-ink-soft">
              {truncate(output)}
            </pre>
          )}

          {!output && argsText && (
            <pre className="scroll-slim max-h-[220px] overflow-auto px-3 py-2.5 font-mono text-[10.5px] leading-[1.75] whitespace-pre-wrap text-ink-muted">
              {truncate(argsText)}
            </pre>
          )}

          {complete && output && (
            <div className="flex items-center gap-1.5 border-t border-line/70 px-3 py-1.5 text-[10px] text-ink-muted">
              <Check className="size-3 text-link" aria-hidden="true" />
              工具已完成
            </div>
          )}
        </div>
      )}
    </div>
  )
}
