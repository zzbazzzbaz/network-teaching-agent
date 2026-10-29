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

import { useChatSession, type ChatStream } from "./useChatSession"

function messageText(message: AppendMessage): string {
  return message.content
    .filter(
      (part): part is { type: "text"; text: string } => part.type === "text",
    )
    .map((part) => part.text)
    .join("\n")
    .trim()
}

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

  const messages = useExternalMessageConverter({
    callback: convertLangChainBaseMessage,
    messages: stream.messages,
    isRunning: stream.isLoading,
  })

  const runtime = useExternalStoreRuntime({
    messages,
    isRunning: stream.isLoading,
    adapters: { attachments: attachmentAdapter },
    onNew: async (message: AppendMessage) => {
      const text = messageText(message)
      const attachments = message.attachments ?? []
      const markers = attachments.map(
        (attachment) => `[图片] ${attachment.name} (file_id=${attachment.id})`,
      )
      const content = [text, ...markers].filter(Boolean).join("\n\n")
      if (!content) return

      await stream.submit({
        messages: [
          {
            type: "human",
            id: crypto.randomUUID(),
            content,
            additional_kwargs: {
              attachments: attachments.map((attachment) => ({
                file_id: attachment.id,
                name: attachment.name,
                mime: attachment.contentType ?? "",
              })),
            },
          },
        ],
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
