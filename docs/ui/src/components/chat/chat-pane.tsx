import { Fragment, useCallback, useLayoutEffect, useRef } from "react"

import { Markdown } from "@/components/chat/markdown"
import { CheckpointCard } from "@/components/chat/checkpoint-card"
import { Composer } from "@/components/chat/composer"
import { ToolTrace } from "@/components/chat/tool-trace"
import { LayerMark } from "@/components/brand"
import { Button } from "@/components/ui/button"
import {
  starters,
  type ChatMessage,
  type Mode,
  type Session,
} from "@/lib/mock"
import { useStore } from "@/lib/store"
import { cn, formatDate, relativeDay } from "@/lib/utils"
type Group = { role: "user" | "assistant"; messages: ChatMessage[] }

function groupMessages(messages: ChatMessage[]) {
  const groups: Group[] = []
  for (const message of messages) {
    const last = groups.at(-1)
    if (last && last.role === "assistant" && message.role === "assistant") {
      last.messages.push(message)
    } else {
      groups.push({ role: message.role, messages: [message] })
    }
  }
  return groups
}

export function ChatPane({ session, mode }: { session: Session; mode: Mode }) {
  const { messagesFor, phaseFor, sendMessage, stop } = useStore()
  const messages = messagesFor(session.id)
  const phase = phaseFor(session.id)
  const groups = groupMessages(messages)
  const scrollRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)

  const checkpointOpen = messages.some((message) =>
    message.parts.some(
      (part) => part.kind === "checkpoint" && !part.checkpoint.submitted,
    ),
  )

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const element = scrollRef.current
    if (!element) return
    element.scrollTo({ top: element.scrollHeight, behavior })
  }, [])

  useLayoutEffect(() => {
    stickToBottom.current = true
    scrollToBottom()
  }, [session.id, scrollToBottom])

  useLayoutEffect(() => {
    if (stickToBottom.current) scrollToBottom()
  }, [messages, phase, scrollToBottom])

  const firstDate = messages[0]?.createdAt
  const dayLabel = firstDate
    ? relativeDay(firstDate) === "今天"
      ? "今天"
      : formatDate(firstDate)
    : "今天"
  const isEmpty = groups.length === 0 && phase === "idle"

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-surface">
      <div
        ref={scrollRef}
        onScroll={(event) => {
          const element = event.currentTarget
          stickToBottom.current =
            element.scrollHeight - element.scrollTop - element.clientHeight < 96
        }}
        className="scroll-slim min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain"
      >
        <div
          className={cn(
            "mx-auto w-full max-w-[904px] px-4 py-5 lg:px-8 lg:py-7",
            isEmpty && "flex min-h-full flex-col justify-center",
          )}
        >
          {groups.length === 0 && phase === "idle" ? (
            <EmptyChat mode={mode} onSend={(text) => sendMessage(session, text)} />
          ) : (
            <>
              {messages.length > 0 && (
                <div
                  className="mb-6 flex items-center gap-3 text-[10.5px] text-ink-muted"
                  aria-hidden="true"
                >
                  <span className="h-px flex-1 bg-line" />
                  <span>{dayLabel}</span>
                  <span className="h-px flex-1 bg-line" />
                </div>
              )}

              <ol className="m-0 list-none p-0">
                {groups.map((group, index) => {
                  const isFirst = index === 0
                  const isLast = index === groups.length - 1
                  const streaming =
                    group.role === "assistant" &&
                    group.messages.some((message) => message.streaming)
                  const key = group.messages[0].id

                  return (
                    <li
                      key={key}
                      className={cn(
                        "relative pl-7 lg:pl-8",
                        group.role === "user"
                          ? index === 0
                            ? ""
                            : "mt-7"
                          : "mt-5",
                      )}
                    >
                      {!(isFirst && isLast) && (
                        <span
                          aria-hidden="true"
                          className={cn(
                            "absolute left-[3px] w-px trace-line",
                            isFirst && "top-[11px] bottom-0",
                            isLast && "top-0 h-[11px]",
                            !isFirst && !isLast && "inset-y-0",
                          )}
                        />
                      )}
                      <span
                        aria-hidden="true"
                        className={cn(
                          "absolute top-2 left-0 size-[7px] rounded-full ring-2 ring-surface",
                          group.role === "assistant"
                            ? "bg-link"
                            : "bg-ink/40",
                          streaming && "link-pulse",
                        )}
                      />

                      {group.role === "user" ? (
                        <div className="ml-auto w-fit max-w-[86%] rounded-lg border border-line bg-surface-2 px-3.5 py-2.5 text-[14px] leading-7 break-words whitespace-pre-wrap text-ink">
                          {group.messages.map((message) => (
                            <Fragment key={message.id}>
                              {message.parts.map((part, partIndex) =>
                                part.kind === "text" ? (
                                  <p key={partIndex} className="whitespace-pre-wrap">
                                    {part.text}
                                  </p>
                                ) : null,
                              )}
                            </Fragment>
                          ))}
                        </div>
                      ) : (
                        <div className="flex min-w-0 flex-col gap-3">
                          {group.messages.map((message) =>
                            message.parts.map((part, partIndex) => {
                              if (part.kind === "text") {
                                return (
                                  <Markdown
                                    key={`${message.id}-${partIndex}`}
                                    text={part.text}
                                    className={cn(
                                      message.streaming &&
                                        partIndex === message.parts.length - 1 &&
                                        "streaming-caret",
                                    )}
                                  />
                                )
                              }
                              if (part.kind === "tool") {
                                return (
                                  <ToolTrace key={part.tool.id} tool={part.tool} />
                                )
                              }
                              return (
                                <CheckpointCard
                                  key={part.id}
                                  session={session}
                                  messageId={message.id}
                                  partId={part.id}
                                  checkpoint={part.checkpoint}
                                />
                              )
                            }),
                          )}
                        </div>
                      )}
                    </li>
                  )
                })}

                {phase === "thinking" && (
                  <li className="relative mt-5 pl-7 lg:pl-8" role="status" aria-live="polite">
                    <span
                      aria-hidden="true"
                      className="absolute top-2 left-0 size-[7px] rounded-full bg-link link-pulse ring-2 ring-surface"
                    />
                    <div className="flex items-center gap-2 text-[12px] text-ink-muted">
                      <span>
                        {mode === "learn" ? "老师正在想" : "Agent 正在处理"}
                      </span>
                      <span className="flex items-center gap-1" aria-hidden="true">
                        <span className="size-1 animate-pulse rounded-full bg-ink-muted [animation-delay:0ms]" />
                        <span className="size-1 animate-pulse rounded-full bg-ink-muted [animation-delay:160ms]" />
                        <span className="size-1 animate-pulse rounded-full bg-ink-muted [animation-delay:320ms]" />
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="ml-1 h-7 px-2 text-[11.5px]"
                        onClick={() => stop(session.id)}
                      >
                        停止
                      </Button>
                    </div>
                  </li>
                )}
              </ol>
            </>
          )}
        </div>
      </div>

      <Composer
        mode={mode}
        busy={phase !== "idle"}
        checkpointOpen={checkpointOpen}
        empty={groups.length === 0}
        onSend={(text) => sendMessage(session, text)}
        onStop={() => stop(session.id)}
      />
    </div>
  )
}

function EmptyChat({
  mode,
  onSend,
}: {
  mode: Mode
  onSend: (text: string) => void
}) {
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
        {starters[mode].slice(0, 3).map((starter) => (
          <button
            key={starter}
            type="button"
            onClick={() => onSend(starter)}
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
