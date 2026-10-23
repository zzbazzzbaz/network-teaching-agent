import { ComposerPrimitive, ThreadPrimitive } from "@assistant-ui/react";
import { useNavigate } from "@tanstack/react-router";

import { AskHumanCard } from "./AskHumanCard";
import { useChatStream } from "./chat-stream-context";
import { AssistantMessage, UserMessage } from "./MessageParts";
import { TodoPanel } from "./TodoPanel";
import { usePendingInterrupt } from "./usePendingInterrupt";

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

export function ChatView({ threadId }: { threadId: string | undefined }) {
  const navigate = useNavigate();
  const pending = usePendingInterrupt();
  const pendingInterrupt = threadId ? pending : undefined;

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-dot" />
          <span>苏格拉底式学习助手</span>
        </div>
        <div className="header-right">
          <span className="thread-id" data-testid="thread-id">
            {threadId ? threadId.slice(0, 8) : "新会话"}
          </span>
          <button
            type="button"
            className="ghost-button"
            data-testid="new-thread"
            onClick={() => {
              void navigate({ to: "/", search: {}, replace: true });
            }}
          >
            新会话
          </button>
        </div>
      </header>

      <div className="app-body">
        <main className="chat">
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
              {pendingInterrupt ? <AskHumanCard /> : <Composer />}
            </div>
          </ThreadPrimitive.Root>
        </main>

        <TodoPanel />
      </div>
    </div>
  );
}
