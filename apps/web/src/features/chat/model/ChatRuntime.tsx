import { useEffect, useMemo, useRef, type ReactNode } from "react"
import {
  AssistantRuntimeProvider,
  useExternalMessageConverter,
  useExternalStoreRuntime,
  type AppendMessage,
} from "@assistant-ui/react"
import { convertLangChainBaseMessage } from "@assistant-ui/react-langchain"
import { useQueryClient } from "@tanstack/react-query"

import { ImageAttachmentAdapter } from "@/features/files/attachment"
import { DEFAULT_SESSION_TITLE, sessionKeys } from "@/features/sessions"
import type { Session } from "@/shared/api/types"

import { buildHumanMessage, messageAttachments, messageText, stripMediaParts } from "./message"
import { usePendingStarter } from "./usePendingStarter"
import { useChatSession, type ChatStream } from "./useChatSession"

export function ChatRuntime({
  session,
  children,
}: {
  session: Session
  children: (stream: ChatStream) => ReactNode
}) {
  const stream = useChatSession({
    agentId: session.agent_id,
    threadId: session.session_id,
  })
  usePendingStarter(session.session_id, stream)
  const queryClient = useQueryClient()
  const wasRunning = useRef(false)
  const attachmentAdapter = useMemo(() => new ImageAttachmentAdapter(), [])

  useEffect(() => {
    const finished = wasRunning.current && !stream.isLoading
    wasRunning.current = stream.isLoading
    if (!finished) return
    if ((session.title || DEFAULT_SESSION_TITLE) !== DEFAULT_SESSION_TITLE) return
    void queryClient.invalidateQueries({
      queryKey: sessionKeys.detail(session.session_id),
    })
    void queryClient.invalidateQueries({
      queryKey: sessionKeys.list(session.agent_id),
    })
  }, [
    stream.isLoading,
    session.session_id,
    session.agent_id,
    session.title,
    queryClient,
  ])

  const displayMessages = useMemo(
    () => stream.messages.map(stripMediaParts),
    [stream.messages],
  )

  const messages = useExternalMessageConverter({
    callback: convertLangChainBaseMessage,
    messages: displayMessages,
    isRunning: stream.isLoading,
  })

  const runtime = useExternalStoreRuntime({
    messages,
    isRunning: stream.isLoading,
    adapters: { attachments: attachmentAdapter },
    onNew: async (message: AppendMessage) => {
      const text = messageText(message)
      const attachments = messageAttachments(message)
      if (!text && attachments.length === 0) return

      await stream.submit({
        messages: [buildHumanMessage(text, attachments)],
      })
    },
    onCancel: async () => {
      await stream.stop()
    },
    convertMessage: (message) => message,
  })

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children(stream)}
    </AssistantRuntimeProvider>
  )
}
