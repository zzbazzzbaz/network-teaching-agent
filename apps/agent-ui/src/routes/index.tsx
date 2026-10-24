import { useCallback, useEffect, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";

import { ChatPage } from "@/features/chat";
import {
  createChatSession,
  deleteChatSession,
  getChatSession,
  listSessions,
  touchChatSession,
} from "@/features/sessions";
import { ApiError } from "@/shared/http";
import { ensureLangGraphThread } from "@/shared/langgraph";

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
  component: ChatRoute,
});

function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (error.status === 403 || error.status === 404 || error.status === 409) {
      return "会话不存在或无权访问";
    }
    return error.message;
  }
  if (error instanceof TypeError) return "无法连接服务器，请确认服务已启动";
  return fallback;
}

function ChatRoute() {
  const { threadId } = Route.useSearch();
  const navigate = Route.useNavigate();

  const [threadReady, setThreadReady] = useState(false);
  const [threadError, setThreadError] = useState<string | null>(null);
  const bootRef = useRef(false);
  const ensureSeq = useRef(0);

  const loadThread = useCallback(
    async (id: string | undefined) => {
      // 没有 threadId：优先进入最近会话，没有会话则创建一个。
      if (id === undefined) {
        if (bootRef.current) return;
        bootRef.current = true;
        setThreadReady(false);
        setThreadError(null);
        try {
          const sessions = await listSessions();
          if (sessions.length > 0) {
            void navigate({
              to: "/",
              search: { threadId: sessions[0].session_id },
              replace: true,
            });
            return;
          }
          const created = await createChatSession("新会话");
          try {
            await ensureLangGraphThread(created.session_id);
          } catch (error) {
            await deleteChatSession(created.session_id).catch(() => undefined);
            throw error;
          }
          void navigate({
            to: "/",
            search: { threadId: created.session_id },
            replace: true,
          });
        } catch (error) {
          bootRef.current = false;
          setThreadError(errorText(error, "创建会话失败，请重试"));
        }
        return;
      }

      // 从“无会话”进入具体会话后，允许下次回到“无会话”时重新 bootstrap。
      bootRef.current = false;

      // 打开某个 session 前先确认它属于当前用户，并补建 LangGraph 线程。
      const seq = ++ensureSeq.current;
      setThreadReady(false);
      setThreadError(null);
      try {
        await getChatSession(id);
        await ensureLangGraphThread(id);
        await touchChatSession(id).catch(() => undefined);
        if (seq === ensureSeq.current) setThreadReady(true);
      } catch (error) {
        if (seq === ensureSeq.current) {
          setThreadError(errorText(error, "加载会话失败，请重试"));
        }
      }
    },
    [navigate],
  );

  useEffect(() => {
    // 会话加载由 URL 驱动，属于与外部系统同步的场景。
    // oxlint-disable-next-line react/set-state-in-effect
    void loadThread(threadId);
  }, [loadThread, threadId]);

  const handleThreadIdChange = useCallback(
    (id: string | undefined) => {
      if (!id) return;
      void navigate({
        to: "/",
        search: { threadId: id },
        replace: true,
      });
    },
    [navigate],
  );

  const handleRetry = useCallback(() => {
    bootRef.current = false;
    void loadThread(threadId);
  }, [loadThread, threadId]);

  return (
    <ChatPage
      threadId={threadId}
      threadReady={threadId !== undefined && threadReady}
      threadError={threadError}
      onThreadIdChange={handleThreadIdChange}
      onRetry={handleRetry}
    />
  );
}
