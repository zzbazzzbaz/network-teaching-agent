import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useExternalMessageConverter,
  useExternalStoreRuntime,
  type AppendMessage,
} from "@assistant-ui/react";
import { convertLangChainBaseMessage } from "@assistant-ui/react-langchain";
import { useStream } from "@langchain/react";

import { ChatStreamContext } from "./chat-stream-context";

const ASSISTANT_ID = "agent";
const API_URL = new URL("/agent", window.location.origin).href;

function messageText(message: AppendMessage): string {
  return message.content
    .filter(
      (part): part is { type: "text"; text: string } => part.type === "text",
    )
    .map((part) => part.text)
    .join("\n")
    .trim();
}

export function ChatRuntimeProvider({
  threadId,
  onThreadIdChange,
  children,
}: {
  threadId: string | undefined;
  onThreadIdChange: (threadId: string | undefined) => void;
  children: ReactNode;
}) {
  const stream = useStream({
    assistantId: ASSISTANT_ID,
    apiUrl: API_URL,
    threadId: threadId ?? null,
    onThreadId: onThreadIdChange,
    maxReconnectAttempts: 2,
  });

  const messages = useExternalMessageConverter({
    callback: convertLangChainBaseMessage,
    messages: stream.messages,
    isRunning: stream.isLoading,
  });

  const runtime = useExternalStoreRuntime({
    messages,
    isRunning: stream.isLoading,
    onNew: async (message: AppendMessage) => {
      const text = messageText(message);
      if (!text) return;
      await stream.submit({
        messages: [{ type: "human", content: text }],
      });
    },
    onCancel: async () => {
      await stream.stop();
    },
    convertMessage: (message) => message,
  });

  return (
    <ChatStreamContext.Provider value={stream}>
      <AssistantRuntimeProvider runtime={runtime}>
        {children}
      </AssistantRuntimeProvider>
    </ChatStreamContext.Provider>
  );
}
