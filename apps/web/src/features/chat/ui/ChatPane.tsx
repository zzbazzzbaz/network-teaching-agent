import { useAui, useAuiState, AuiIf, ThreadPrimitive } from "@assistant-ui/react"
import { AlertCircle } from "lucide-react"

import type { Mode, Session } from "@/shared/api/types"
import { LayerMark } from "@/shared/ui/brand"
import { cn } from "@/shared/lib/utils"

import { ChatRuntime } from "../model/ChatRuntime"
import { pendingInterrupt } from "../model/interrupt"
import type { ChatStream } from "../model/useChatSession"
import { AskStudentCard } from "./AskStudentCard"
import { Composer } from "./Composer"
import { AssistantMessage, UserMessage } from "./MessageParts"

const STARTERS: Record<Mode, string[]> = {
  learn: [
    "TCP 为什么需要三次握手？",
    "子网掩码和广播地址怎么算？",
    "HTTP/2 的多路复用解决了什么？",
  ],
  lab: [
    "我想用 tcpdump 观察一次 TCP 握手。",
    "怎么确认一个端口有没有在监听？",
    "想写一个最小的 UDP 回声服务器。",
  ],
}

function EmptyChat({ mode }: { mode: Mode }) {
  const aui = useAui()

  function send(text: string) {
    const composer = aui.thread.composer()
    composer.setText(text)
    void composer.send()
  }

  return (
    <div className="flex flex-col items-start py-10 lg:py-16">
      <LayerMark className="size-6 text-link" />
      <h2 className="mt-5 text-[18px] font-semibold text-ink">
        {mode === "learn" ? "从一句话开始" : "先说你想验证什么"}
      </h2>
      <p className="mt-2 max-w-[38ch] text-[13px] leading-6 text-ink-muted">
        {mode === "learn"
          ? "不用先组织好。把你现在理解到的部分说出来，老师会从那里接着问。"
          : "不用先写完整命令。告诉我你想观察什么现象，我们从最小的一步开始。"}
      </p>

      <div className="mt-6 w-full max-w-[560px] border-t border-line">
        {STARTERS[mode].map((starter) => (
          <button
            key={starter}
            type="button"
            onClick={() => send(starter)}
            className="group flex w-full items-center gap-3 border-b border-line py-3 text-left hover:bg-surface-2/70"
          >
            <span
              aria-hidden="true"
              className="size-1.5 rounded-full border border-line-strong group-hover:border-link group-hover:bg-link"
            />
            <span className="min-w-0 flex-1 text-[13px] text-ink-soft group-hover:text-ink">
              {starter}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

function ErrorBanner({ stream }: { stream: ChatStream }) {
  if (!stream.error) return null
  return (
    <div
      role="alert"
      className="mx-4 mb-2 flex items-start gap-2 rounded-md border border-danger-line bg-danger-soft px-3 py-2 text-[11.5px] leading-5 text-danger lg:mx-auto lg:w-full lg:max-w-[840px]"
    >
      <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
      <span>
        {stream.error instanceof Error
          ? stream.error.message
          : String(stream.error)}
      </span>
    </div>
  )
}

function ChatSurface({
  mode,
  stream,
}: {
  mode: Mode
  stream: ChatStream
}) {
  const empty = useAuiState((state) => state.thread.isEmpty)
  const pending = pendingInterrupt(stream)

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col bg-surface">
      <ThreadPrimitive.Root className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
        <ThreadPrimitive.Viewport className="scroll-slim min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain">
          <div
            className={cn(
              "mx-auto w-full max-w-[1080px] px-4 py-5 lg:px-8 lg:py-7 xl:px-10",
              empty && "flex min-h-full flex-col justify-center",
            )}
          >
            <AuiIf condition={(state) => state.thread.isEmpty}>
              <EmptyChat mode={mode} />
            </AuiIf>

            <div className="thread-messages">
              <ThreadPrimitive.Messages
                components={{
                  UserMessage,
                  AssistantMessage,
                }}
              />
            </div>

            {!pending ? (
              <AuiIf condition={(state) => state.thread.isRunning}>
                <div
                  className="relative mt-5 flex items-center gap-2 pl-7 text-[12px] text-ink-muted lg:pl-8"
                  role="status"
                  aria-live="polite"
                >
                  <span
                    aria-hidden="true"
                    className="absolute top-1.5 left-0 size-[7px] rounded-full bg-link link-pulse ring-2 ring-surface"
                  />
                  <span>{mode === "learn" ? "老师正在想" : "Agent 正在处理"}</span>
                  <span className="flex items-center gap-1" aria-hidden="true">
                    <span className="size-1 animate-pulse rounded-full bg-ink-muted [animation-delay:0ms]" />
                    <span className="size-1 animate-pulse rounded-full bg-ink-muted [animation-delay:160ms]" />
                    <span className="size-1 animate-pulse rounded-full bg-ink-muted [animation-delay:320ms]" />
                  </span>
                </div>
              </AuiIf>
            ) : null}
          </div>
        </ThreadPrimitive.Viewport>

        <ErrorBanner stream={stream} />

        {pending ? (
          <div className="shrink-0 border-t border-line bg-surface px-4 py-3 lg:px-8">
            <div className="mx-auto w-full max-w-[1000px]">
              <AskStudentCard
                key={pending.id ?? "ask-student"}
                interrupt={pending}
                stream={stream}
              />
            </div>
          </div>
        ) : null}

        <Composer mode={mode} empty={empty} disabled={Boolean(pending)} />
      </ThreadPrimitive.Root>
    </div>
  )
}

export function ChatPane({
  session,
  mode,
  onUserMessage,
}: {
  session: Session
  mode: Mode
  onUserMessage?: (text: string) => void
}) {
  return (
    <ChatRuntime session={session} onUserMessage={onUserMessage}>
      {(stream) => <ChatSurface mode={mode} stream={stream} />}
    </ChatRuntime>
  )
}
