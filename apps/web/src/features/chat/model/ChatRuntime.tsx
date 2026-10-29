import type { ReactNode } from "react"
import {
  AssistantRuntimeProvider,
  useExternalMessageConverter,
  useExternalStoreRuntime,
  type AppendMessage,
} from "@assistant-ui/react"
import { convertLangChainBaseMessage } from "@assistant-ui/react-langchain"

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
  onUserMessage,
  children,
}: {
  session: Session
  onUserMessage?: (text: string) => void
  children: (stream: ChatStream) => ReactNode
}) {
  const stream = useChatSession({
    agentId: session.agent_id,
    threadId: session.session_id,
  })

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
      onUserMessage?.(text)
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
