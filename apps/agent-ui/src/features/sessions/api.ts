/** 会话列表接口：平台 session_id 同时作为 LangGraph thread_id。 */

import { apiFetch } from "@/shared/http";

export interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export function listSessions(): Promise<ChatSession[]> {
  return apiFetch<ChatSession[]>("/sessions");
}

export function getChatSession(sessionId: string): Promise<ChatSession> {
  return apiFetch<ChatSession>(`/sessions/${sessionId}`);
}

export function createChatSession(title = "新会话"): Promise<ChatSession> {
  return apiFetch<ChatSession>("/sessions", {
    method: "POST",
    body: { title },
  });
}

export function renameChatSession(sessionId: string, title: string): Promise<ChatSession> {
  return apiFetch<ChatSession>(`/sessions/${sessionId}`, {
    method: "PATCH",
    body: { title },
  });
}

export function touchChatSession(sessionId: string): Promise<void> {
  return apiFetch<void>(`/sessions/${sessionId}/touch`, { method: "POST" });
}

export function deleteChatSession(sessionId: string): Promise<void> {
  return apiFetch<void>(`/sessions/${sessionId}`, { method: "DELETE" });
}
