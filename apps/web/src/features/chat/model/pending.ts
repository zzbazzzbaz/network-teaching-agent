import type { MessageAttachment } from "./message"

export type PendingMessage = {
  text: string
  attachments: MessageAttachment[]
}

/**
 * 草稿首页不建会话，首条消息先暂存在内存里，
 * 进入会话页、thread 准备好之后再发出去。
 */
const pending = new Map<string, PendingMessage>()

export function setPendingMessage(
  sessionId: string,
  message: PendingMessage,
): void {
  pending.set(sessionId, message)
}

export function peekPendingMessage(
  sessionId: string,
): PendingMessage | undefined {
  return pending.get(sessionId)
}

export function clearPendingMessage(sessionId: string): void {
  pending.delete(sessionId)
}
