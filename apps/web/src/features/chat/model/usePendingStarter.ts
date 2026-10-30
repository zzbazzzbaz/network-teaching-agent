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
  const { error, isThreadLoading, messages, submit } = stream

  useEffect(() => {
    const pending = pendingRef.current
    if (!pending || submittedRef.current) return
    if (isThreadLoading) return

    submittedRef.current = true
    pendingRef.current = null
    clearPendingMessage(sessionId)

    if (error || messages.length > 0) return
    void submit({
      messages: [buildHumanMessage(pending.text, pending.attachments)],
    })
  }, [error, isThreadLoading, messages.length, sessionId, submit])
}
