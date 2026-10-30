import {
  AlertCircle,
  ChevronRight,
  FileText,
  Folder,
  FolderOpen,
  RefreshCw,
} from "lucide-react"
import { useState } from "react"

import { humanizeApiError } from "@/shared/api/errors"
import { cn, formatSize } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/shared/ui/collapsible"

import type { MemoryTreeNode } from "../model/tree"

function treeErrorMessage(error: unknown): string {
  return humanizeApiError(error, "读取记忆目录失败", {
    503: "记忆服务暂不可用",
  })
}

export function MemoryTree({
  nodes,
  fileCount,
  selectedPath,
  isLoading,
  error,
  onRetry,
  onSelect,
}: {
  nodes: readonly MemoryTreeNode[]
  fileCount: number
  selectedPath?: string
  isLoading: boolean
  error: unknown
  onRetry: () => void
  onSelect: (path: string) => void
}) {
  const showError = !isLoading && Boolean(error) && nodes.length === 0

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-line bg-surface">
      <div className="flex shrink-0 items-center gap-2 border-b border-line px-3.5 py-2.5">
        <span className="font-mono text-[10.5px] text-ink-muted">/memory</span>
        <span className="ml-auto text-[10.5px] text-ink-muted">
          {isLoading ? "读取中" : `${fileCount} 个文件`}
        </span>
      </div>

      <nav
        aria-label="记忆文件"
        className="scroll-slim min-h-0 flex-1 overflow-y-auto px-2 py-2"
      >
        {isLoading ? (
          <TreeLoading />
        ) : showError ? (
          <TreeError error={error} onRetry={onRetry} />
        ) : nodes.length === 0 ? (
          <TreeEmpty />
        ) : (
          nodes.map((entry) =>
            entry.kind === "directory" ? (
              <FolderNode
                key={entry.path}
                entry={entry}
                level={0}
                selectedPath={selectedPath}
                onSelect={onSelect}
              />
            ) : (
              <FileNode
                key={entry.path}
                entry={entry}
                level={0}
                selected={selectedPath === entry.path}
                onSelect={onSelect}
              />
            ),
          )
        )}
      </nav>
    </aside>
  )
}

function TreeLoading() {
  return (
    <div className="px-1 py-2" role="status" aria-label="正在读取记忆目录">
      {Array.from({ length: 5 }, (_, index) => (
        <div
          key={index}
          className="mt-1 h-8 animate-pulse rounded-sm bg-surface-2"
          style={{
            marginLeft: index % 2 === 0 ? 0 : 12,
            width: index % 2 === 0 ? "100%" : "84%",
          }}
        />
      ))}
    </div>
  )
}

function TreeEmpty() {
  return (
    <div className="px-3 py-10 text-center">
      <Folder className="mx-auto size-5 text-ink-muted/60" aria-hidden="true" />
      <p className="mt-3 text-[12.5px] text-ink-muted">还没有记忆文件</p>
      <p className="mt-1 text-[10.5px] leading-5 text-ink-muted/80">
        Agent 会在学习过程中把重要内容写到这里。
      </p>
    </div>
  )
}

function TreeError({
  error,
  onRetry,
}: {
  error: unknown
  onRetry: () => void
}) {
  return (
    <div className="px-3 py-8 text-center" role="alert">
      <AlertCircle
        className="mx-auto size-5 text-danger/70"
        aria-hidden="true"
      />
      <p className="mt-3 text-[12.5px] text-ink-soft">
        {treeErrorMessage(error)}
      </p>
      <Button
        variant="outline"
        size="sm"
        className="mt-3 h-8 gap-1.5"
        onClick={onRetry}
      >
        <RefreshCw className="size-3.5" aria-hidden="true" />
        重试
      </Button>
    </div>
  )
}

function FolderNode({
  entry,
  level,
  selectedPath,
  onSelect,
}: {
  entry: MemoryTreeNode
  level: number
  selectedPath?: string
  onSelect: (path: string) => void
}) {
  const [open, setOpen] = useState(true)
  const children = entry.children

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
          <Folder
            className="size-3.5 shrink-0 text-ink-muted"
            aria-hidden="true"
          />
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
              onSelect={onSelect}
            />
          ) : (
            <FileNode
              key={child.path}
              entry={child}
              level={level + 1}
              selected={selectedPath === child.path}
              onSelect={onSelect}
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
  onSelect,
}: {
  entry: MemoryTreeNode
  level: number
  selected: boolean
  onSelect: (path: string) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(entry.path)}
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
    </button>
  )
}
