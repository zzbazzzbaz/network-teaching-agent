import type { AIMessage, ToolMessage } from "@langchain/core/messages";

import { useChatStream } from "./chat-stream-context";

/**
 * `stream.interrupt` is replayed from the run history on hydration, so after a
 * reload it can still describe an interrupt that was already answered.
 *
 * An interrupt is only live while the last message is an AI message whose tool
 * call has no matching tool result yet.
 */
export function usePendingInterrupt() {
  const stream = useChatStream();
  const messages = stream.messages;

  const last = messages.at(-1);
  if (!stream.interrupt || last?.getType() !== "ai") return undefined;

  const toolCalls = (last as AIMessage).tool_calls ?? [];
  if (toolCalls.length === 0) return undefined;

  const resultIds = new Set(
    messages
      .filter((message) => message.getType() === "tool")
      .map((message) => (message as ToolMessage).tool_call_id),
  );

  const waiting = toolCalls.some(
    (call) => call.id != null && !resultIds.has(call.id),
  );

  return waiting ? stream.interrupt : undefined;
}
