import { AlertCircle, ArrowLeft, Loader2, RefreshCw } from "lucide-react"

import { ApiError } from "@/shared/api/client"
import { StaticMarkdown } from "@/features/chat"
import { cn, formatDateTime, formatSize } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"

import { useMemoryFile } from "../queries"

const NOTE_MARKDOWN_CLASS = cn(
  "[&_p+p]:mt-3 [&_>*+*]:mt-3",
  "[&_h1]:mt-5 [&_h1]:text-[17px] [&_h1]:font-semibold [&_h1:first-child]:mt-0",
  "[&_h2]:mt-5 [&_h2]:text-[15px] [&_h2]:font-semibold [&_h2:first-child]:mt-0",
  "[&_h3]:mt-4 [&_h3]:text-[14px] [&_h3]:font-semibold [&_h3:first-child]:mt-0",
  "[&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li+_li]:mt-1",
  "[&_a]:text-link [&_a]:underline [&_a]:underline-offset-2",
  "[&_strong]:font-semibold",
  "[&_code]:rounded-sm [&_code]:border [&_code]:border-line [&_code]:bg-surface-2 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.9em]",
  "[&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-line [&_pre]:bg-surface-2 [&_pre]:p-3 [&_pre]:text-[12px] [&_pre]:leading-6 [&_pre_code]:border-0 [&_pre_code]:bg-transparent [&_pre_code]:p-0",
  "[&_blockquote]:border-l-2 [&_blockquote]:border-link-line [&_blockquote]:pl-3 [&_blockquote]:text-ink-soft",
  "[&_hr]:border-line",
)

function fileErrorCopy(error: unknown): { title: string; description: string } {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return {
          title: "文件不存在",
          description: "它可能已经被 Agent 移除，或者链接里的路径不完整。",
        }
      case 413:
        return {
          title: "文件过大",
          description: "这个记忆文件超过 128 KiB，无法在这里预览。",
        }
      case 415:
        return {
          title: "无法预览",
          description: "这个文件不是 UTF-8 文本，暂时只能显示文本类记忆。",
        }
      case 422:
        return {
          title: "路径无效",
          description: "请返回记忆目录，重新选择一个文件。",
        }
      case 503:
        return {
          title: "记忆服务暂不可用",
          description: "文件暂时读不出来，请稍后重试。",
        }
      default:
        return { title: "无法读取文件", description: error.message }
    }
  }
  if (error instanceof TypeError) {
    return {
      title: "无法读取文件",
      description: "无法连接服务器，请确认服务已启动。",
    }
  }
  return { title: "无法读取文件", description: "请稍后重试。" }
}

export function MemoryFilePane({
  path,
  onBack,
}: {
  path: string
  onBack: () => void
}) {
  const fileQuery = useMemoryFile(path)
  const file = fileQuery.data
  const name = file?.name ?? path.split("/").at(-1) ?? path
  const errorCopy = fileQuery.isError ? fileErrorCopy(fileQuery.error) : null

  return (
    <section className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-line bg-surface">
      <div className="shrink-0 border-b border-line px-4 py-3.5 lg:px-5">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-semibold text-ink">
              {name}
            </p>
            <p className="mt-1 truncate font-mono text-[10px] text-ink-muted">
              {file?.path ?? path}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-9 shrink-0 gap-1 lg:hidden"
            onClick={onBack}
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            文件
          </Button>
        </div>
        <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10.5px] text-ink-muted">
          {file ? (
            <>
              {file.modified_at ? (
                <span>更新于 {formatDateTime(file.modified_at)}</span>
              ) : (
                <span>更新时间未知</span>
              )}
              <span className="font-mono">{formatSize(file.size)}</span>
            </>
          ) : fileQuery.isPending ? (
            <span>读取中…</span>
          ) : errorCopy ? (
            <span>无法读取文件信息</span>
          ) : null}
        </p>
      </div>

      <div className="scroll-slim min-h-0 flex-1 overflow-y-auto px-4 py-4 lg:px-5">
        {fileQuery.isPending ? (
          <div
            className="flex min-h-[220px] flex-col items-center justify-center gap-2 text-[12px] text-ink-muted"
            role="status"
          >
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            正在读取文件…
          </div>
        ) : errorCopy ? (
          <div
            className="flex min-h-[240px] flex-col items-center justify-center px-6 py-12 text-center"
            role="alert"
          >
            <AlertCircle
              className="size-6 text-danger/65"
              aria-hidden="true"
            />
            <p className="mt-3 text-[13px] font-medium text-ink">
              {errorCopy.title}
            </p>
            <p className="mt-1 max-w-[38ch] text-[11.5px] leading-5 text-ink-muted">
              {errorCopy.description}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4 h-8 gap-1.5"
              onClick={() => void fileQuery.refetch()}
            >
              <RefreshCw className="size-3.5" aria-hidden="true" />
              重试
            </Button>
          </div>
        ) : file ? (
          file.content.trim() ? (
            <StaticMarkdown
              text={file.content}
              tone="note"
              className={NOTE_MARKDOWN_CLASS}
            />
          ) : (
            <p className="py-10 text-center text-[12.5px] text-ink-muted">
              这个文件是空的。
            </p>
          )
        ) : null}
      </div>
    </section>
  )
}
