import {
  AlertCircle,
  Check,
  Code2,
  Copy,
  ExternalLink,
  Info,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Terminal,
  Trash2,
} from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import type { Sandbox } from "@/shared/api/types"
import { cn, formatDateTime } from "@/shared/lib/utils"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"

import {
  sandboxErrorMessage,
  STATUS_DOT,
  STATUS_HINT,
  STATUS_LABEL,
  type SandboxDisplayStatus,
} from "../model"

export function SandboxDetails({
  sandbox,
  busy,
  starting,
  pausing,
  destroying,
  onStart,
  onPause,
  onDestroy,
}: {
  sandbox: Sandbox
  busy: boolean
  starting: boolean
  pausing: boolean
  destroying: boolean
  onStart: () => void
  onPause: () => void
  onDestroy: () => void
}) {
  const [copied, setCopied] = useState(false)
  const status = sandbox.status
  const running = status === "running"
  const paused = status === "paused"
  const stopping = status === "stopping"
  const vscodeUrl = running ? sandbox.vscode_url : null
  const ttydUrl = running ? sandbox.ttyd_url : null

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 1_600)
    return () => window.clearTimeout(timer)
  }, [copied])

  async function copyId() {
    try {
      await navigator.clipboard.writeText(sandbox.sandbox_id)
      setCopied(true)
      toast("已复制沙盒 ID")
    } catch {
      toast.error("复制失败，请手动选择")
    }
  }

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-surface">
      <SandboxHeader status={status} />

      <div className="px-5 py-5">
        <p className="text-[10.5px] text-ink-muted">沙盒 ID</p>
        <div className="mt-0.5 flex items-start gap-1.5">
          <span className="min-w-0 font-mono text-[12px] leading-5 break-all text-ink-soft">
            {sandbox.sandbox_id}
          </span>
          <button
            type="button"
            onClick={() => void copyId()}
            aria-label="复制沙盒 ID"
            className="shrink-0 rounded-sm p-1 text-ink-muted hover:bg-surface-3 hover:text-ink"
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
              : "正在释放沙盒资源。完成后 workspace 会被清空。"}
        </p>

        <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-line pt-4 text-[11px]">
          <Meta label="最后活跃" value={formatDateTime(sandbox.last_active_at)} />
          <Meta label="保活到期" value={formatDateTime(sandbox.expires_at)} />
          {sandbox.paused_at ? (
            <Meta label="暂停于" value={formatDateTime(sandbox.paused_at)} />
          ) : null}
          <Meta
            label="最迟销毁"
            value={formatDateTime(sandbox.hard_destroy_at)}
          />
          <Meta label="心跳间隔" value={`每 ${sandbox.heartbeat_seconds} 秒`} />
        </dl>

        {stopping ? (
          <p className="mt-4 flex items-center gap-1.5 text-[11px] text-ink-muted">
            <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
            正在等待销毁完成，页面每 10 秒自动刷新。
          </p>
        ) : null}
      </div>

      {vscodeUrl || ttydUrl ? (
        <div className="grid gap-2 px-5 pb-5 sm:grid-cols-2">
          {vscodeUrl ? (
            <OpenTile
              href={vscodeUrl}
              title="VSCode"
              description="在浏览器中打开编辑器"
              icon="code"
            />
          ) : null}
          {ttydUrl ? (
            <OpenTile
              href={ttydUrl}
              title="终端"
              description="运行实验命令"
              icon="terminal"
            />
          ) : null}
        </div>
      ) : null}

      {running || paused ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-line bg-surface-2/50 px-5 py-3">
          {running ? (
            <Button
              variant="outline"
              size="sm"
              className="h-9 gap-1.5"
              disabled={busy}
              onClick={onPause}
            >
              {pausing ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Pause className="size-3.5" aria-hidden="true" />
              )}
              {pausing ? "暂停中…" : "暂停沙盒"}
            </Button>
          ) : (
            <Button
              size="sm"
              className="h-9 gap-1.5"
              disabled={busy}
              onClick={onStart}
            >
              {starting ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <RotateCcw className="size-3.5" aria-hidden="true" />
              )}
              {starting ? "恢复中…" : "恢复沙盒"}
            </Button>
          )}

          <Button
            variant="destructive-outline"
            size="sm"
            className="h-9 gap-1.5"
            disabled={busy}
            onClick={onDestroy}
          >
            {destroying ? (
              <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="size-3.5" aria-hidden="true" />
            )}
            销毁
          </Button>

          <span className="ml-auto hidden text-[10.5px] text-ink-muted sm:block">
            暂停保留文件，销毁会清空 workspace
          </span>
        </div>
      ) : null}
    </section>
  )
}

export function SandboxIdle({
  starting,
  onStart,
}: {
  starting: boolean
  onStart: () => void
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-surface">
      <SandboxHeader status="idle" />
      <div className="px-5 py-5">
        <p className="text-[13px] leading-6 text-ink-soft">
          还没有启动实验沙盒。
        </p>
        <p className="mt-1.5 text-[12.5px] leading-6 text-ink-muted">
          启动后会在云端创建一个 workspace，可以打开 VSCode 或终端继续实验。
        </p>
        <Button
          className="mt-5 h-10 w-full gap-2 sm:w-auto"
          disabled={starting}
          onClick={onStart}
        >
          {starting ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Play className="size-3.5" aria-hidden="true" />
          )}
          {starting ? "启动中…" : "启动沙盒"}
        </Button>
      </div>
    </section>
  )
}

export function SandboxLoading() {
  return (
    <section
      className="flex items-center justify-center gap-2 rounded-lg border border-line bg-surface px-5 py-16 text-[12.5px] text-ink-muted"
      role="status"
    >
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      正在读取沙盒状态…
    </section>
  )
}

export function SandboxError({
  error,
  onRetry,
}: {
  error: unknown
  onRetry: () => void
}) {
  return (
    <section
      className="rounded-lg border border-line bg-surface px-5 py-12 text-center"
      role="alert"
    >
      <AlertCircle
        className="mx-auto size-6 text-danger/65"
        aria-hidden="true"
      />
      <p className="mt-3 text-[13px] font-medium text-ink">
        无法读取沙盒状态
      </p>
      <p className="mt-1 text-[11.5px] leading-5 text-ink-muted">
        {sandboxErrorMessage(error, "请稍后重试。")}
      </p>
      <Button
        variant="outline"
        size="sm"
        className="mt-4 h-8 gap-1.5"
        onClick={onRetry}
      >
        <RefreshCw className="size-3.5" aria-hidden="true" />
        重试
      </Button>
    </section>
  )
}

export function AccountNote() {
  return (
    <div className="mt-4 flex items-start gap-2 rounded-md border border-line bg-surface-2/60 px-3.5 py-3 text-[11px] leading-5 text-ink-muted">
      <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
      <p>
        沙盒按账户创建，所有实验会话共享同一个 workspace。删除会话不会删除这里的文件。
      </p>
    </div>
  )
}

function SandboxHeader({ status }: { status: SandboxDisplayStatus }) {
  const hint = STATUS_HINT[status]

  return (
    <div className="flex items-center gap-2 border-b border-line px-5 py-3">
      <span
        aria-hidden="true"
        className={cn("size-2 rounded-full", STATUS_DOT[status])}
      />
      <span className="text-[13px] font-medium text-ink">
        {STATUS_LABEL[status]}
      </span>
      <Badge variant="outline" className="ml-1">
        账户级
      </Badge>
      {hint ? (
        <span className="ml-auto text-[10.5px] text-ink-muted">{hint}</span>
      ) : null}
    </div>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-ink-muted">{label}</dt>
      <dd className="mt-0.5 text-ink-soft">{value}</dd>
    </div>
  )
}

function OpenTile({
  href,
  title,
  description,
  icon,
}: {
  href: string
  title: string
  description: string
  icon: "code" | "terminal"
}) {
  const Icon = icon === "code" ? Code2 : Terminal

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 rounded-md border border-line bg-surface px-3 py-2.5 transition-colors hover:border-link-line hover:bg-surface-2/50 focus-visible:ring-2 focus-visible:ring-ring/30"
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-line bg-surface-2 text-ink-muted">
        <Icon className="size-4" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[12.5px] font-medium text-ink">
          {title}
        </span>
        <span className="mt-0.5 block text-[10.5px] text-ink-muted">
          {description}
        </span>
      </span>
      <ExternalLink
        className="size-3.5 shrink-0 text-ink-muted"
        aria-hidden="true"
      />
    </a>
  )
}
