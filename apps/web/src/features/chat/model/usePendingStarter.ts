import { useEffect, useRef } from "react"

import { buildHumanMessage } from "./message"
import { clearPendingMessage, peekPendingMessage, type PendingMessage } from "./pending"
import type { ChatStream } from "./useChatSession"

/**
 * 消费草稿首页留下的首条消息。
 * 只在 thread 历史加载完、且会话为空时发送；发送前先清掉暂存，避免重复。
 */
export function usePendingStarter(
  sessionId: string,
  stream: ChatStream,
): void {
  const pendingRef = useRef<PendingMessage | null | undefined>(undefined)
  if (pendingRef.current === undefined) {
    pendingRef.current = peekPendingMessage(sessionId) ?? null
  }
  const submittedRef = useRef(false)
  const inFlightRef = useRef(false)
  const { error, isThreadLoading, messages, submit } = stream

  useEffect(() => {
    const pending = pendingRef.current
    if (!pending || submittedRef.current || isThreadLoading || inFlightRef.current) {
      return
    }

    // 会话已经有历史消息，草稿消息不应再插入，直接丢弃。
    if (messages.length > 0) {
      pendingRef.current = null
      submittedRef.current = true
      clearPendingMessage(sessionId)
      return
    }

    // thread 加载失败时保留 pending，等用户重试或刷新后继续发送。
    if (error) return

    inFlightRef.current = true
    void submit({
      messages: [buildHumanMessage(pending.text, pending.attachments)],
    })
      .then(() => {
        pendingRef.current = null
        submittedRef.current = true
        clearPendingMessage(sessionId)
      })
      .catch(() => {
        // 发送失败保留 pending，避免首条消息静默丢失。
      })
      .finally(() => {
        inFlightRef.current = false
      })
  }, [error, isThreadLoading, messages.length, sessionId, submit])
}
