import type { AppendMessage } from "@assistant-ui/react"
import { useNavigate } from "@tanstack/react-router"
import { useRef, useState } from "react"
import { toast } from "sonner"

import { useCreateSession } from "@/features/sessions"
import { humanizeApiError } from "@/shared/api/errors"
import type { Mode } from "@/shared/api/types"

import {
  messageAttachments,
  messageText,
  type MessageAttachment,
} from "./message"
import { setPendingMessage } from "./pending"

function errorText(error: unknown): string {
  return humanizeApiError(error, "创建会话失败")
}

/**
 * 草稿首页的建会话入口：首条消息发出前不创建 session。
 * 建完后把消息暂存起来，由会话页在 thread 就绪后发出。
 */
export function useDraftConversation(mode: Mode) {
  const navigate = useNavigate()
  const create = useCreateSession(mode)
  const [startingId, setStartingId] = useState<string | null>(null)
  const startingRef = useRef(false)

  async function start(
    text: string,
    attachments: MessageAttachment[],
    title: string,
    busyId: string,
  ) {
    if (startingRef.current) return
    startingRef.current = true
    setStartingId(busyId)

    try {
      const session = await create.mutateAsync({ title })
      setPendingMessage(session.session_id, { text, attachments })
      try {
        if (mode === "learn") {
          await navigate({
            to: "/learn/$sessionId",
            params: { sessionId: session.session_id },
            replace: true,
          })
        } else {
          await navigate({
            to: "/lab/$sessionId",
            params: { sessionId: session.session_id },
            replace: true,
          })
        }
      } catch {
        startingRef.current = false
        setStartingId(null)
        toast.error("会话已创建，但打开失败，请从左侧会话列表打开。")
      }
    } catch (error) {
      startingRef.current = false
      setStartingId(null)
      toast.error(errorText(error))
    }
  }

  async function startFromMessage(message: AppendMessage) {
    const text = messageText(message)
    const attachments = messageAttachments(message)
    if (!text && attachments.length === 0) return
    await start(text, attachments, "", "draft")
  }

  return {
    starting: startingId !== null,
    startingId,
    start,
    startFromMessage,
  }
}
