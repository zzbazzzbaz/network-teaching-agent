import { useEffect, useRef, type ReactNode } from "react"
import {
  AssistantRuntimeProvider,
  useExternalMessageConverter,
  useExternalStoreRuntime,
  type AppendMessage,
} from "@assistant-ui/react"
import { convertLangChainBaseMessage } from "@assistant-ui/react-langchain"
import { useQueryClient } from "@tanstack/react-query"

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
    onNew: async (message: AppendMessage) => {
      const text = messageText(message)
      if (!text) return
      await stream.submit({
        messages: [{ type: "human", content: text }],
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
