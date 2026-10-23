import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useExternalMessageConverter,
  useExternalStoreRuntime,
  type AppendMessage,
} from "@assistant-ui/react";
import { convertLangChainBaseMessage } from "@assistant-ui/react-langchain";

import { useChatSession } from "../api/useChatSession";
import { ChatStreamContext } from "./chat-stream-context";

function messageText(message: AppendMessage): string {
  return message.content
    .filter(
      (part): part is { type: "text"; text: string } => part.type === "text",
    )
    .map((part) => part.text)
    .join("\n")
    .trim();
}

/**
 * Bridges the LangChain stream into an assistant-ui runtime.
 * UI components never touch the transport directly.
 */
export function ChatRuntimeProvider({
  threadId,
  onThreadIdChange,
  children,
}: {
  threadId: string | undefined;
  onThreadIdChange: (threadId: string | undefined) => void;
  children: ReactNode;
}) {
  const stream = useChatSession({ threadId, onThreadIdChange });

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
