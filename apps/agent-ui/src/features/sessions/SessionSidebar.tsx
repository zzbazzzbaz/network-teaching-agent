import * as React from "react";
import { useNavigate } from "@tanstack/react-router";

import { ApiError } from "@/shared/http";
import {
  deleteLangGraphThread,
  ensureLangGraphThread,
} from "@/shared/langgraph";

import {
  createChatSession,
  deleteChatSession,
  listSessions,
  renameChatSession,
  type ChatSession,
} from "./api";

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "无法连接服务器，请确认服务已启动";
  return fallback;
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SessionSidebar({ activeThreadId }: { activeThreadId: string | undefined }) {
  const navigate = useNavigate();
  const [sessions, setSessions] = React.useState<ChatSession[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [creating, setCreating] = React.useState(false);
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editingTitle, setEditingTitle] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const loadSeq = React.useRef(0);

  const load = React.useCallback(async () => {
    const seq = ++loadSeq.current;
    try {
      const items = await listSessions();
      if (seq === loadSeq.current) {
        setSessions(items);
        setError(null);
      }
    } catch (err) {
      if (seq === loadSeq.current) setError(errorMessage(err, "加载会话列表失败"));
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    void load();
  }, [load]);

  const goToSession = (sessionId: string) => {
    void navigate({ to: "/", search: { threadId: sessionId } });
  };

  const handleCreate = async () => {
    if (creating) return;
    setCreating(true);
    setError(null);
    let created: ChatSession | null = null;
    try {
      created = await createChatSession("新会话");
      await ensureLangGraphThread(created.session_id);
      await load();
      goToSession(created.session_id);
    } catch (err) {
      if (created !== null) {
        // 运行时线程创建失败时，不留下一个打不开的空会话。
        await deleteChatSession(created.session_id).catch(() => undefined);
      }
      setError(errorMessage(err, "创建会话失败"));
    } finally {
      setCreating(false);
    }
  };

  const startRename = (session: ChatSession) => {
    setEditingId(session.session_id);
    setEditingTitle(session.title || "新会话");
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditingTitle("");
  };

  const saveRename = async (session: ChatSession) => {
    const title = editingTitle.trim() || "新会话";
    if (title === session.title) {
      cancelRename();
      return;
    }
    setBusyId(session.session_id);
    setError(null);
    try {
      await renameChatSession(session.session_id, title);
      await load();
      cancelRename();
    } catch (err) {
      setError(errorMessage(err, "重命名失败"));
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (session: ChatSession) => {
    if (!window.confirm(`确定删除会话「${session.title || "新会话"}」吗？`)) return;
    setBusyId(session.session_id);
    setError(null);
    try {
      await deleteLangGraphThread(session.session_id);
      await deleteChatSession(session.session_id);
      await load();
      if (session.session_id === activeThreadId) {
        void navigate({ to: "/", search: {} });
      }
    } catch (err) {
      setError(errorMessage(err, "删除会话失败"));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <aside className="session-sidebar" data-testid="session-sidebar">
      <div className="session-sidebar-header">
        <span>会话</span>
        <button
          type="button"
          className="session-new"
          onClick={() => void handleCreate()}
          disabled={creating}
          data-testid="session-new"
        >
          {creating ? "创建中…" : "＋ 新建"}
        </button>
      </div>

      {error !== null && (
        <div className="session-error" role="alert">
          {error}
        </div>
      )}

      <div className="session-list">
        {loading ? (
          <div className="session-empty">加载中…</div>
        ) : sessions.length === 0 ? (
          <div className="session-empty" data-testid="session-empty">
            还没有会话
          </div>
        ) : (
          sessions.map((session) => {
            const active = session.session_id === activeThreadId;
            const busy = busyId === session.session_id;
            return (
              <div
                key={session.session_id}
                className={`session-item${active ? " session-item-active" : ""}`}
                data-testid="session-item"
                data-session-id={session.session_id}
              >
                {editingId === session.session_id ? (
                  <div className="session-edit">
                    <input
                      value={editingTitle}
                      onChange={(event) => setEditingTitle(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          void saveRename(session);
                        }
                        if (event.key === "Escape") cancelRename();
                      }}
                      maxLength={100}
                      autoFocus
                      data-testid="session-rename-input"
                    />
                    <div className="session-edit-actions">
                      <button
                        type="button"
                        onClick={() => void saveRename(session)}
                        disabled={busy}
                        data-testid="session-rename-save"
                      >
                        保存
                      </button>
                      <button type="button" onClick={cancelRename} disabled={busy}>
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      className="session-select"
                      onClick={() => goToSession(session.session_id)}
                      disabled={busy}
                      data-testid="session-select"
                    >
                      <span className="session-title" data-testid="session-title">
                        {session.title || "新会话"}
                      </span>
                      <span className="session-time">{formatWhen(session.updated_at)}</span>
                    </button>
                    <div className="session-actions">
                      <button
                        type="button"
                        onClick={() => startRename(session)}
                        disabled={busy}
                        data-testid="session-rename"
                      >
                        重命名
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDelete(session)}
                        disabled={busy}
                        data-testid="session-delete"
                      >
                        删除
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
