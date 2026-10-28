import {
  Check,
  Code2,
  Copy,
  ExternalLink,
  Info,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  Terminal,
  Trash2,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { sandbox } from "@/lib/mock"
import { useStore } from "@/lib/store"
import { cn, formatDateTime } from "@/lib/utils"

type Busy = "start" | "pause" | "destroy" | null

export function SandboxPanel() {
  const { sandboxState, setSandboxState } = useStore()
  const [busy, setBusy] = useState<Busy>(null)
  const [copied, setCopied] = useState(false)
  const [confirmDestroy, setConfirmDestroy] = useState(false)
  const timers = useRef<number[]>([])

  useEffect(() => {
    const pending = timers.current
    return () => {
      for (const timer of pending) window.clearTimeout(timer)
    }
  }, [])

  function run(next: "running" | "paused" | "stopped", action: Busy, message: string) {
    setBusy(action)
    const timer = window.setTimeout(() => {
      setSandboxState(next)
      setBusy(null)
      toast(message)
    }, 900)
    timers.current.push(timer)
  }

  async function copyId() {
    try {
      await navigator.clipboard.writeText(sandbox.id)
      setCopied(true)
      toast("已复制沙盒 ID")
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      toast.error("复制失败，请手动选择")
    }
  }

  const running = sandboxState === "running"
  const paused = sandboxState === "paused"
  const stopped = sandboxState === "stopped"

  return (
    <div className="scroll-slim h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-[960px] px-5 py-7 lg:px-10 lg:py-9">
        <h2 className="text-[24px] leading-tight font-semibold tracking-[-0.015em] text-ink">
          实验沙盒
        </h2>

        <div className="mt-6 max-w-[760px]">
          <section className="overflow-hidden rounded-lg border border-line bg-surface">
            <div className="flex items-center gap-2 border-b border-line px-5 py-3">
              <span
                aria-hidden="true"
                className={cn(
                  "size-2 rounded-full",
                  running && "bg-link",
                  paused && "bg-signal",
                  stopped && "bg-line-strong",
                )}
              />
              <span className="text-[13px] font-medium text-ink">
                {running ? "运行中" : paused ? "已暂停" : "已销毁"}
              </span>
              <Badge variant="outline" className="ml-1">
                账户级
              </Badge>
              {!running && (
                <span className="ml-auto text-[10.5px] text-ink-muted">
                  {paused ? "文件保留" : "无活动沙盒"}
                </span>
              )}
            </div>

            <div className="px-5 pt-5">
              <h3 className="text-[20px] font-semibold tracking-[-0.01em] text-ink">
                {sandbox.name}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <span className="font-mono text-[10.5px] text-ink-muted">
                  {sandbox.id}
                </span>
                <button
                  type="button"
                  onClick={copyId}
                  aria-label="复制沙盒 ID"
                  className="rounded-sm p-1 text-ink-muted hover:bg-surface-3 hover:text-ink"
                >
                  {copied ? (
                    <Check className="size-3 text-link" aria-hidden="true" />
                  ) : (
                    <Copy className="size-3" aria-hidden="true" />
                  )}
                </button>
              </div>

              <p className="mt-3 text-[12.5px] leading-6 text-ink-muted">
                {running
                  ? "可以打开 VSCode 或终端继续实验。暂停会释放计算资源，但保留文件。"
                  : paused
                    ? "workspace 已冻结。恢复后才能打开 VSCode 和终端。"
                    : "启动会创建一个新的 workspace，旧文件不会恢复。"}
              </p>

              <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-line pt-4 text-[11px]">
                <div>
                  <dt className="text-ink-muted">创建于</dt>
                  <dd className="mt-0.5 text-ink-soft">
                    {formatDateTime(sandbox.createdAt)}
                  </dd>
                </div>
                <div>
                  <dt className="text-ink-muted">最后活跃</dt>
                  <dd className="mt-0.5 text-ink-soft">
                    {stopped ? "—" : formatDateTime(sandbox.lastActiveAt)}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="px-5 py-5">
              {!stopped ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  <OpenTile
                    href={sandbox.vscodeUrl}
                    title="VSCode"
                    description="在浏览器中打开编辑器"
                    icon="code"
                    disabled={!running}
                  />
                  <OpenTile
                    href={sandbox.terminalUrl}
                    title="终端"
                    description="运行实验命令"
                    icon="terminal"
                    disabled={!running}
                  />
                </div>
              ) : (
                <Button
                  className="h-10 w-full gap-2 sm:w-auto"
                  disabled={busy !== null}
                  onClick={() => run("running", "start", "沙盒已启动")}
                >
                  {busy === "start" ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Play className="size-3.5" aria-hidden="true" />
                  )}
                  {busy === "start" ? "启动中…" : "启动沙盒"}
                </Button>
              )}
            </div>

            {!stopped && (
              <div className="flex flex-wrap items-center gap-2 border-t border-line bg-surface-2/50 px-5 py-3">
                {running ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-9 gap-1.5"
                    disabled={busy !== null}
                    onClick={() => run("paused", "pause", "沙盒已暂停")}
                  >
                    {busy === "pause" ? (
                      <Loader2
                        className="size-3.5 animate-spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <Pause className="size-3.5" aria-hidden="true" />
                    )}
                    暂停沙盒
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    className="h-9 gap-1.5"
                    disabled={busy !== null}
                    onClick={() => run("running", "start", "沙盒已恢复")}
                  >
                    {busy === "start" ? (
                      <Loader2
                        className="size-3.5 animate-spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <RotateCcw className="size-3.5" aria-hidden="true" />
                    )}
                    恢复沙盒
                  </Button>
                )}

                <Button
                  variant="destructive-outline"
                  size="sm"
                  className="h-9 gap-1.5"
                  disabled={busy !== null}
                  onClick={() => setConfirmDestroy(true)}
                >
                  <Trash2 className="size-3.5" aria-hidden="true" />
                  销毁
                </Button>

                <span className="ml-auto hidden text-[10.5px] text-ink-muted sm:block">
                  暂停保留文件，销毁会清空 workspace
                </span>
              </div>
            )}
          </section>

          <div className="mt-4 flex items-start gap-2 rounded-md border border-line bg-surface-2/60 px-3.5 py-3 text-[11px] leading-5 text-ink-muted">
            <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            <p>
              沙盒按账户创建，所有实验会话共享同一个 workspace。删除会话不会删除这里的文件。
            </p>
          </div>
        </div>
      </div>

      <AlertDialog open={confirmDestroy} onOpenChange={setConfirmDestroy}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>销毁沙盒？</AlertDialogTitle>
            <AlertDialogDescription>
              所有实验会话共享这个 workspace。销毁后，其中的文件、代码和终端历史都无法恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmDestroy(false)
                run("stopped", "destroy", "沙盒已销毁")
              }}
            >
              销毁沙盒
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function OpenTile({
  href,
  title,
  description,
  icon,
  disabled,
}: {
  href: string
  title: string
  description: string
  icon: "code" | "terminal"
  disabled: boolean
}) {
  const Icon = icon === "code" ? Code2 : Terminal

  const content = (
    <>
      <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-line bg-surface-2 text-ink-muted">
        <Icon className="size-4" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[12.5px] font-medium text-ink">{title}</span>
        <span className="mt-0.5 block text-[10.5px] text-ink-muted">
          {disabled ? "恢复沙盒后才能打开" : description}
        </span>
      </span>
      <ExternalLink
        className={cn(
          "size-3.5 shrink-0",
          disabled ? "text-ink-muted/40" : "text-ink-muted",
        )}
        aria-hidden="true"
      />
    </>
  )

  if (disabled) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-line bg-surface-2/40 px-3 py-2.5 opacity-60">
        {content}
      </div>
    )
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 rounded-md border border-line bg-surface px-3 py-2.5 transition-colors hover:border-link-line hover:bg-surface-2/50 focus-visible:ring-2 focus-visible:ring-ring/30"
    >
      {content}
    </a>
  )
}
