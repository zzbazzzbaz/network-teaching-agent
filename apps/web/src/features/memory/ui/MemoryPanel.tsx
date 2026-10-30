import { FileText } from "lucide-react"
import { useEffect, useMemo } from "react"

import { useMediaQuery } from "@/shared/lib/hooks"
import { cn } from "@/shared/lib/utils"
import {
  WorkspaceHeader,
  workspaceContentClass,
} from "@/shared/ui/workspace-header"

import { buildMemoryTree, DEFAULT_MEMORY_FILE } from "../model/tree"
import { useMemoryTree } from "../queries"
import { MemoryFilePane } from "./MemoryFilePane"
import { MemoryTree } from "./MemoryTree"

export interface MemoryPanelProps {
  path?: string
  onPathChange: (
    path: string | undefined,
    options?: { replace?: boolean },
  ) => void
}

export function MemoryPanel({ path, onPathChange }: MemoryPanelProps) {
  const isWide = useMediaQuery("(min-width: 1024px)")
  const treeQuery = useMemoryTree()
  const entries = treeQuery.data?.entries
  const filePath = path || undefined

  const tree = useMemo(
    () => (entries ? buildMemoryTree(entries) : []),
    [entries],
  )
  const files = useMemo(
    () => entries?.filter((entry) => entry.kind === "file") ?? [],
    [entries],
  )
  const defaultPath = useMemo(() => {
    const profile = files.find((entry) => entry.path === DEFAULT_MEMORY_FILE)
    return profile?.path ?? files[0]?.path
  }, [files])

  useEffect(() => {
    if (!isWide || filePath || !defaultPath) return
    // 自动选中默认文件只替换当前历史记录，避免浏览器后退再次触发自动选中。
    onPathChange(defaultPath, { replace: true })
  }, [defaultPath, filePath, isWide, onPathChange])

  function backToTree() {
    onPathChange(undefined)
  }

  const showTree = isWide || !filePath
  const showFile = isWide || Boolean(filePath)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <WorkspaceHeader title="记忆" />

      <div className="min-h-0 flex-1">
        <div
          className={cn(
            workspaceContentClass,
            "flex h-full min-h-0 flex-col py-5 lg:py-6",
          )}
        >
          <div className="grid h-full min-h-0 w-full gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
            {showTree ? (
              <MemoryTree
                nodes={tree}
                fileCount={files.length}
                selectedPath={filePath}
                isLoading={treeQuery.isPending}
                error={treeQuery.isError ? treeQuery.error : null}
                onRetry={() => void treeQuery.refetch()}
                onSelect={(nextPath) => onPathChange(nextPath)}
              />
            ) : null}

            {showFile ? (
              filePath ? (
                <MemoryFilePane
                  key={filePath}
                  path={filePath}
                  onBack={backToTree}
                />
              ) : (
                <FilePlaceholder />
              )
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

function FilePlaceholder() {
  return (
    <section className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-line bg-surface">
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
    </section>
  )
}
