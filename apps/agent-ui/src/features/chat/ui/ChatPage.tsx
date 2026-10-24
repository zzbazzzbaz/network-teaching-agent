import { useState } from "react";
import { ComposerPrimitive, ThreadPrimitive } from "@assistant-ui/react";

import { useAuth } from "@/features/auth";
import { SessionSidebar } from "@/features/sessions";

import { useChatStream } from "../model/chat-stream-context";
import { ChatRuntimeProvider } from "../model/ChatRuntimeProvider";
import { usePendingInterrupt } from "../model/usePendingInterrupt";
import { AskHumanCard } from "./AskHumanCard";
import { AssistantMessage, UserMessage } from "./MessageParts";
import { TodoPanel } from "./TodoPanel";

function ErrorBanner() {
  const stream = useChatStream();
  if (!stream.error) return null;
  return (
    <div className="error-banner" data-testid="error-banner">
      {stream.error instanceof Error
        ? stream.error.message
        : String(stream.error)}
    </div>
  );
}

function Composer() {
  return (
    <ComposerPrimitive.Root className="composer">
      <ComposerPrimitive.Input
        className="composer-input"
        data-testid="composer-input"
        placeholder="说说你卡在哪里，或者让我考考你…"
        rows={2}
        submitMode="enter"
      />
      <ComposerPrimitive.Send
        className="composer-send"
        data-testid="composer-send"
      >
        发送
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}

function ThreadView() {
  const pending = usePendingInterrupt();

  return (
    <ThreadPrimitive.Root className="thread">
      <ThreadPrimitive.Viewport className="viewport">
        <ThreadPrimitive.Empty>
          <div className="empty" data-testid="empty-state">
            <div className="empty-title">从一个问题开始</div>
            <div className="empty-hint">
              例如：帮我理解 TCP 三次握手，为什么需要第三次？
            </div>
          </div>
        </ThreadPrimitive.Empty>

        <ThreadPrimitive.Messages
          components={{ UserMessage, AssistantMessage }}
        />
      </ThreadPrimitive.Viewport>

      <ErrorBanner />

      <ThreadPrimitive.If running>
        <div className="running" data-testid="running-indicator">
          <span />
          <span />
          <span />
        </div>
      </ThreadPrimitive.If>

      <div className="footer">
        {pending !== undefined ? <AskHumanCard /> : <Composer />}
      </div>
    </ThreadPrimitive.Root>
  );
}

export function ChatPage({
  threadId,
  threadReady,
  threadError,
  onThreadIdChange,
  onRetry,
}: {
  threadId: string | undefined;
  threadReady: boolean;
  threadError: string | null;
  onThreadIdChange: (threadId: string | undefined) => void;
  onRetry: () => void;
}) {
  const { session, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 900);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <button
            type="button"
            className="ghost-button"
            data-testid="session-toggle"
            onClick={() => setSidebarOpen((open) => !open)}
          >
            会话
          </button>
          <div className="brand">
            <span className="brand-dot" />
            <span>苏格拉底式学习助手</span>
          </div>
        </div>
        <div className="header-right">
          <span className="thread-id" data-testid="thread-id">
            {threadId ? threadId.slice(0, 8) : "新会话"}
          </span>
          <span className="current-user" data-testid="current-user">
            {session?.username ?? ""}
          </span>
          <button
            type="button"
            className="ghost-button"
            data-testid="logout-button"
            onClick={logout}
          >
            退出
          </button>
        </div>
      </header>

      <div className="app-body">
        {sidebarOpen && <SessionSidebar activeThreadId={threadId} />}

        {threadError !== null ? (
          <main className="chat">
            <div className="chat-status" data-testid="chat-error">
              <div className="chat-status-title">无法打开这个会话</div>
              <div className="chat-status-detail">{threadError}</div>
              <button type="button" className="ghost-button" onClick={onRetry}>
                重试
              </button>
            </div>
          </main>
        ) : !threadReady ? (
          <main className="chat">
            <div className="chat-status" data-testid="chat-loading">
              正在加载会话…
            </div>
          </main>
        ) : (
          <ChatRuntimeProvider
            threadId={threadId}
            onThreadIdChange={onThreadIdChange}
          >
            <main className="chat">
              <ThreadView />
            </main>
            <TodoPanel />
          </ChatRuntimeProvider>
        )}
      </div>
    </div>
  );
}
