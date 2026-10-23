import { useCallback } from "react";
import { createFileRoute } from "@tanstack/react-router";

import { ChatRuntimeProvider } from "@/features/chat/ChatRuntimeProvider";
import { ChatView } from "@/features/chat/ChatView";

type ChatSearch = {
  threadId?: string;
};

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): ChatSearch => ({
    threadId:
      typeof search.threadId === "string" && search.threadId.length > 0
        ? search.threadId
        : undefined,
  }),
  component: ChatPage,
});

function ChatPage() {
  const { threadId } = Route.useSearch();
  const navigate = Route.useNavigate();

  const handleThreadIdChange = useCallback(
    (id: string | undefined) => {
      if (!id) return;
      void navigate({
        to: "/",
        search: (prev) => ({ ...prev, threadId: id }),
        replace: true,
      });
    },
    [navigate],
  );

  return (
    <ChatRuntimeProvider
      threadId={threadId}
      onThreadIdChange={handleThreadIdChange}
    >
      <ChatView threadId={threadId} />
    </ChatRuntimeProvider>
  );
}
