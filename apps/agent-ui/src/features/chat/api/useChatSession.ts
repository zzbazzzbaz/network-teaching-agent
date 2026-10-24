import { useMemo } from "react";
import { useStream } from "@langchain/react";

import { createLangGraphClient } from "@/shared/langgraph";

const ASSISTANT_ID = "agent";

/**
 * Owns the LangGraph session: transport, thread identity, reconnection.
 * This is the only module that knows where the agent lives.
 */
export function useChatSession({
  threadId,
  onThreadIdChange,
}: {
  threadId: string | undefined;
  onThreadIdChange: (threadId: string | undefined) => void;
}) {
  const client = useMemo(() => createLangGraphClient(), []);

  return useStream({
    client,
    assistantId: ASSISTANT_ID,
    threadId: threadId ?? null,
    onThreadId: onThreadIdChange,
    maxReconnectAttempts: 2,
  });
}
