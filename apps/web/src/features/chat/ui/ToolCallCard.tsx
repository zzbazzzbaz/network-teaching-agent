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
import { useState } from "react"
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
    const question = argString(args, ["question"])
    const resultText = pretty(result)
    const answer = /学生答案[：:]\s*([\s\S]*?)(?:\n参考答案[：:]|\n（题库记录失败|$)/.exec(
      resultText,
    )?.[1]?.trim()
    if (!question || !answer) return null
    const preview = answer.length > 500 ? `${answer.slice(0, 500)}…` : answer
    return (
      <div className="w-full max-w-[640px] overflow-hidden rounded-lg border border-link-line bg-surface-2/70">
        <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
          <CheckCircle2 className="size-3.5 text-link" aria-hidden="true" />
          <span className="text-[11px] text-ink-muted">已作答</span>
          <span className="ml-auto font-mono text-[10px] text-ink-muted/70">
            ask_student
          </span>
        </div>
        <div className="px-4 py-3">
          <p className="line-clamp-2 text-[12.5px] leading-5 text-ink-soft">
            {question}
          </p>
          <p className="mt-2 max-h-40 overflow-y-auto text-[11.5px] leading-5 whitespace-pre-wrap text-ink-muted">
            你的作答：{preview}
          </p>
        </div>
      </div>
    )
  }

  const Icon = iconFor(toolName)
  const command = argString(args, ["command", "cmd"])
  const output = pretty(result)
  const argsText = pretty(args)
  const hasDetail = Boolean(command || output || argsText)
  const summary = summaryFor(toolName, args)
  const complete = status.type === "complete" && !isError

  return (
    <div className="w-full max-w-[640px] overflow-hidden rounded-md border border-line bg-surface-2/60">
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
