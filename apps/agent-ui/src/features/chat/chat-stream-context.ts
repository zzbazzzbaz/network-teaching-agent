import { createContext, useContext } from "react";
import type { useStream } from "@langchain/react";

export type ChatStream = ReturnType<typeof useStream>;

export const ChatStreamContext = createContext<ChatStream | null>(null);

export function useChatStream(): ChatStream {
  const stream = useContext(ChatStreamContext);
  if (!stream) {
    throw new Error("useChatStream must be used inside <ChatRuntimeProvider>");
  }
  return stream;
}
