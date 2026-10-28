import {
  ArrowLeft,
  ChevronRight,
  FileText,
  Folder,
  FolderOpen,
} from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"

import { Markdown } from "@/components/chat/markdown"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { useMediaQuery } from "@/lib/hooks"
import {
  memoryEntries,
  memoryFiles,
  type MemoryEntry,
} from "@/lib/mock"
import { cn, formatDateTime, formatSize } from "@/lib/utils"

const DEFAULT_FILE = "/memory/profile.md"

function childrenOf(path: string) {
  return memoryEntries
    .filter((entry) => {
      if (entry.path === "/memory/") return false
      const trimmed = entry.path.endsWith("/")
        ? entry.path.slice(0, -1)
        : entry.path
      const parent = trimmed.slice(0, trimmed.lastIndexOf("/") + 1)
      return parent === path
    })
    .toSorted((a, b) => {
      if (a.kind !== b.kind) return a.kind === "directory" ? -1 : 1
      return a.name.localeCompare(b.name, "zh-CN")
    })
}

export function MemoryPanel() {
  const [params, setParams] = useSearchParams()
  const isWide = useMediaQuery("(min-width: 1024px)")
  const filePath = params.get("path")
  const file = filePath ? memoryFiles[filePath] : undefined
  const files = memoryEntries.filter((entry) => entry.kind === "file")

  useEffect(() => {
    if (!isWide || filePath) return
    const next = new URLSearchParams(params)
    next.set("panel", "memory")
    next.set("path", DEFAULT_FILE)
    setParams(next, { replace: true })
  }, [isWide, filePath, params, setParams])

  function backToTree() {
    const next = new URLSearchParams(params)
    next.delete("path")
    next.set("panel", "memory")
    setParams(next)
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-line bg-surface">
        <div className="mx-auto w-full max-w-[960px] px-5 py-5 lg:px-10 lg:py-6">
          <h2 className="text-[24px] leading-tight font-semibold tracking-[-0.015em] text-ink">
            记忆
          </h2>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <div className="mx-auto flex h-full min-h-0 w-full max-w-[960px] flex-col px-5 pb-5 lg:px-10 lg:pb-6">
          <div className="grid h-full min-h-0 w-full gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
            {(isWide || !file) && (
            <aside className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-line bg-surface">
              <div className="flex shrink-0 items-center gap-2 border-b border-line px-3.5 py-2.5">
                <span className="font-mono text-[10.5px] text-ink-muted">
                  /memory
                </span>
                <span className="ml-auto text-[10.5px] text-ink-muted">
                  {files.length} 个文件
                </span>
              </div>

              <nav
                aria-label="记忆文件"
                className="scroll-slim min-h-0 flex-1 overflow-y-auto px-2 py-2"
              >
                {files.length === 0 ? (
                  <div className="px-3 py-10 text-center">
                    <Folder
                      className="mx-auto size-5 text-ink-muted/60"
                      aria-hidden="true"
                    />
                    <p className="mt-3 text-[12.5px] text-ink-muted">
                      还没有记忆文件
                    </p>
                  </div>
                ) : (
                  childrenOf("/memory/").map((entry) =>
                    entry.kind === "directory" ? (
                      <FolderNode
                        key={entry.path}
                        entry={entry}
                        level={0}
                        selectedPath={filePath}
                      />
                    ) : (
                      <FileNode
                        key={entry.path}
                        entry={entry}
                        level={0}
                        selected={filePath === entry.path}
                      />
                    ),
                  )
                )}
              </nav>
            </aside>
          )}

          {(isWide || file) && (
            <section className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-line bg-surface">
              {file ? (
                <>
                  <div className="shrink-0 border-b border-line px-4 py-3.5 lg:px-5">
                    <div className="flex items-start gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[15px] font-semibold text-ink">
                          {file.path.split("/").at(-1)}
                        </p>
                        <p className="mt-1 truncate font-mono text-[10px] text-ink-muted">
                          {file.path}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-9 shrink-0 gap-1 lg:hidden"
                        onClick={backToTree}
                      >
                        <ArrowLeft className="size-3.5" aria-hidden="true" />
                        文件
                      </Button>
                    </div>
                    <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10.5px] text-ink-muted">
                      <span>更新于 {formatDateTime(file.modifiedAt)}</span>
                      <span className="font-mono">{formatSize(file.size)}</span>
                    </p>
                  </div>

                  <div className="scroll-slim min-h-0 flex-1 overflow-y-auto px-4 py-4 lg:px-5">
                    <Markdown text={file.content} className="prose-note" />
                  </div>
                </>
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
                  <FileText
                    className="size-6 text-ink-muted/50"
                    aria-hidden="true"
                  />
                  <p className="mt-3 text-[13px] text-ink-soft">选择一个文件查看</p>
                  <p className="mt-1 text-[11px] text-ink-muted">
                    左侧是 Agent 维护的记忆目录。
                  </p>
                </div>
              )}
            </section>
          )}
          </div>
        </div>
      </div>
    </div>
  )
}

function FolderNode({
  entry,
  level,
  selectedPath,
}: {
  entry: MemoryEntry
  level: number
  selectedPath: string | null
}) {
  const [open, setOpen] = useState(true)
  const children = childrenOf(entry.path)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger
        className="flex h-9 w-full items-center gap-1.5 rounded-sm pr-2 text-left text-[12.5px] text-ink-soft transition-colors hover:bg-surface-2"
        style={{ paddingLeft: 6 + level * 12 }}
      >
        <ChevronRight
          className={cn(
            "size-3.5 shrink-0 text-ink-muted transition-transform",
            open && "rotate-90",
          )}
          aria-hidden="true"
        />
        {open ? (
          <FolderOpen
            className="size-3.5 shrink-0 text-ink-muted"
            aria-hidden="true"
          />
        ) : (
          <Folder className="size-3.5 shrink-0 text-ink-muted" aria-hidden="true" />
        )}
        <span className="truncate">{entry.name}</span>
        <span className="ml-auto font-mono text-[9.5px] text-ink-muted">
          {children.length}
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        {children.map((child) =>
          child.kind === "directory" ? (
            <FolderNode
              key={child.path}
              entry={child}
              level={level + 1}
              selectedPath={selectedPath}
            />
          ) : (
            <FileNode
              key={child.path}
              entry={child}
              level={level + 1}
              selected={selectedPath === child.path}
            />
          ),
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}

function FileNode({
  entry,
  level,
  selected,
}: {
  entry: MemoryEntry
  level: number
  selected: boolean
}) {
  return (
    <Link
      to={`?panel=memory&path=${encodeURIComponent(entry.path)}`}
      aria-current={selected ? "page" : undefined}
      style={{ paddingLeft: 28 + level * 12 }}
      className={cn(
        "flex h-9 w-full items-center gap-1.5 rounded-sm pr-2 text-left text-[12.5px] transition-colors",
        selected
          ? "bg-link-soft font-medium text-link-strong"
          : "text-ink-soft hover:bg-surface-2",
      )}
    >
      <FileText
        className={cn(
          "size-3.5 shrink-0",
          selected ? "text-link" : "text-ink-muted",
        )}
        aria-hidden="true"
      />
      <span className="truncate">{entry.name}</span>
      <span className="ml-auto shrink-0 font-mono text-[9.5px] text-ink-muted">
        {formatSize(entry.size)}
      </span>
    </Link>
  )
}
