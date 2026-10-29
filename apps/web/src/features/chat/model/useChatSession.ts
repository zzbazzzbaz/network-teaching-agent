import { useMemo } from "react"
import { useStream } from "@langchain/react"

import type { AgentId } from "@/shared/api/types"
import { createLangGraphClient } from "@/shared/langgraph/client"

export function useChatSession({
  agentId,
  threadId,
}: {
  agentId: AgentId
  threadId: string
}) {
  const client = useMemo(() => createLangGraphClient(), [])

  return useStream({
    client,
    assistantId: agentId,
    threadId,
    maxReconnectAttempts: 2,
  })
}

export type ChatStream = ReturnType<typeof useChatSession>
