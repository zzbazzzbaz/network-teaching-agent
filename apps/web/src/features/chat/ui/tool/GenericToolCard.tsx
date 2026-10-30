import {
  Check,
  ChevronDown,
  CircleHelp,
  Cloud,
  FileText,
  Search,
  Terminal,
  Wrench,
} from "lucide-react"
import { useMemo, useState } from "react"
import type { ToolCallMessagePartProps } from "@assistant-ui/react"

import { cn } from "@/shared/lib/utils"

import {
  argString,
  pretty,
  statusLabel,
  summaryFor,
  truncate,
} from "../../model/tool-call"

function iconFor(toolName: string) {
  if (toolName.includes("question")) return Search
  if (toolName.includes("execute") || toolName.includes("terminal")) {
    return Terminal
  }
  if (toolName.includes("sandbox")) return Cloud
  if (
    toolName.includes("file") ||
    toolName.includes("read") ||
    toolName.includes("write")
  ) {
    return FileText
  }
  if (toolName === "task") return CircleHelp
  return Wrench
}

export function GenericToolCard({
  toolName,
  args,
  result,
  status,
  isError,
}: ToolCallMessagePartProps) {
  const [open, setOpen] = useState(false)
  const Icon = iconFor(toolName)
  const command = useMemo(
    () => argString(args, ["command", "cmd"]),
    [args],
  )
  const output = useMemo(() => pretty(result), [result])
  const argsText = useMemo(() => pretty(args), [args])
  const summary = useMemo(() => summaryFor(toolName, args), [toolName, args])
  const hasDetail = Boolean(command || output || argsText)
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
