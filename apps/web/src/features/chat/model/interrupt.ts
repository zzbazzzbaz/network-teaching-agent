import { useMemo } from "react"
import type { AIMessage, ToolMessage } from "@langchain/core/messages"

import type { ChatStream } from "./useChatSession"

/**
 * `stream.interrupt` 会从 run history 重放，刷新后可能仍描述一个已经作答的
 * interrupt。只有最后一个 AI 消息里的 tool call 还没有对应 tool result 时，
 * 才把它视为当前待作答中断。
 */
export function pendingInterrupt(stream: ChatStream) {
  const messages = stream.messages
  const last = messages.at(-1)
  if (!stream.interrupt || last?.getType() !== "ai") return undefined

  const toolCalls = (last as AIMessage).tool_calls ?? []
  if (toolCalls.length === 0) return undefined

  const resultIds = new Set(
    messages
      .filter((message) => message.getType() === "tool")
      .map((message) => (message as ToolMessage).tool_call_id),
  )

  const waiting = toolCalls.some(
    (call) => call.id != null && !resultIds.has(call.id),
  )

  return waiting ? stream.interrupt : undefined
}

/**
 * 只依赖会影响 pending 判断的字段，避免每个流式 token 都重新扫描全部消息。
 */
export function pendingInterruptSignature(stream: ChatStream): string {
  const messages = stream.messages
  const last = messages.at(-1)
  const lastType = last?.getType() ?? ""
  const toolIds =
    lastType === "ai"
      ? ((last as AIMessage).tool_calls ?? [])
          .map((call) => call.id ?? "")
          .join(",")
      : ""
  return `${stream.interrupt?.id ?? ""}|${stream.interrupt ? 1 : 0}|${messages.length}|${lastType}|${toolIds}`
}

export function usePendingInterrupt(stream: ChatStream) {
  const signature = pendingInterruptSignature(stream)
  return useMemo(() => pendingInterrupt(stream), [signature])
}
