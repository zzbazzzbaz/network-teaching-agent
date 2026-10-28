import {
  Check,
  ChevronDown,
  CircleHelp,
  FileText,
  Search,
  Terminal,
  Cloud,
} from "lucide-react"
import { useState } from "react"

import { cn } from "@/lib/utils"
import type { ToolPart } from "@/lib/mock"

const ICONS = {
  search: Search,
  question: CircleHelp,
  terminal: Terminal,
  sandbox: Cloud,
  file: FileText,
} as const

export function ToolTrace({ tool }: { tool: ToolPart }) {
  const [open, setOpen] = useState(tool.tool === "terminal")
  const Icon = ICONS[tool.tool]
  const hasDetail = Boolean(tool.command || tool.output || tool.meta?.length)
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
          {tool.name}
        </span>
        <span className="min-w-0 flex-1 truncate text-[11.5px] text-ink-muted">
          {tool.summary}
        </span>
        <span
          className={cn(
            "size-1.5 shrink-0 rounded-full",
            tool.status === "success" && "bg-link",
            tool.status === "running" && "bg-signal link-pulse",
            tool.status === "error" && "bg-danger",
          )}
          aria-hidden="true"
        />
        <span className="sr-only">
          {tool.status === "success"
            ? "成功"
            : tool.status === "running"
              ? "进行中"
              : "失败"}
        </span>
        {tool.duration && (
          <span className="hidden shrink-0 font-mono text-[10px] text-ink-muted sm:block">
            {tool.duration}
          </span>
        )}
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
          {tool.command && (
            <div className="border-b border-line px-3 py-2">
              <span className="font-mono text-[11px] text-ink-muted select-none">
                ${" "}
              </span>
              <span className="font-mono text-[11px] break-all text-ink-soft">
                {tool.command}
              </span>
            </div>
          )}

          {tool.output && (
            <pre className="scroll-slim max-h-[240px] overflow-auto px-3 py-2.5 font-mono text-[10.5px] leading-[1.75] whitespace-pre text-ink-soft">
              {tool.output}
            </pre>
          )}

          {(tool.meta?.length || typeof tool.exitCode === "number") && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line/70 px-3 py-1.5 text-[10.5px] text-ink-muted">
              {typeof tool.exitCode === "number" && (
                <span className="flex items-center gap-1 font-mono">
                  <Check className="size-3 text-link" aria-hidden="true" />
                  exit {tool.exitCode}
                </span>
              )}
              {tool.meta?.map((item) => (
                <span key={item} className="font-mono">
                  {item}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
