import { FileText } from "lucide-react"
import { useEffect, useMemo } from "react"

import { useMediaQuery } from "@/shared/lib/hooks"

import { buildMemoryTree, DEFAULT_MEMORY_FILE } from "../model/tree"
import { useMemoryTree } from "../queries"
import { MemoryFilePane } from "./MemoryFilePane"
import { MemoryTree } from "./MemoryTree"

export interface MemoryPanelProps {
  path?: string
  onPathChange: (path: string | undefined) => void
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
    onPathChange(defaultPath)
  }, [defaultPath, filePath, isWide, onPathChange])

  function backToTree() {
    onPathChange(undefined)
  }

  const showTree = isWide || !filePath
  const showFile = isWide || Boolean(filePath)

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
                <MemoryFilePane path={filePath} onBack={backToTree} />
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
