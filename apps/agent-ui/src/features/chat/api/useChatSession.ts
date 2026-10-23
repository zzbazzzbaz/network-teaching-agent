import { useStream } from "@langchain/react";

const ASSISTANT_ID = "agent";
const API_URL = new URL("/agent", window.location.origin).href;

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
  return useStream({
    assistantId: ASSISTANT_ID,
    apiUrl: API_URL,
    threadId: threadId ?? null,
    onThreadId: onThreadIdChange,
    maxReconnectAttempts: 2,
  });
}
