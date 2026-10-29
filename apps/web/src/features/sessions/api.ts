import { apiFetch } from "@/shared/api/client"
import type { AgentId, Session, SessionPage } from "@/shared/api/types"

export interface ListSessionsParams {
  agentId: AgentId
  limit?: number
  offset?: number
}

export function listSessions({
  agentId,
  limit = 20,
  offset = 0,
}: ListSessionsParams): Promise<SessionPage> {
  const params = new URLSearchParams({
    agent_id: agentId,
    limit: String(limit),
    offset: String(offset),
  })
  return apiFetch<SessionPage>(`/sessions?${params.toString()}`)
}

export function getSession(sessionId: string): Promise<Session> {
  return apiFetch<Session>(`/sessions/${sessionId}`)
}

export function createSession(agentId: AgentId, title = ""): Promise<Session> {
  return apiFetch<Session>("/sessions", {
    method: "POST",
    body: { agent_id: agentId, title },
  })
}

export function renameSession(sessionId: string, title: string): Promise<Session> {
  return apiFetch<Session>(`/sessions/${sessionId}`, {
    method: "PATCH",
    body: { title },
  })
}

export function touchSession(sessionId: string): Promise<void> {
  return apiFetch<void>(`/sessions/${sessionId}/touch`, { method: "POST" })
}

export function deleteSession(sessionId: string): Promise<void> {
  return apiFetch<void>(`/sessions/${sessionId}`, { method: "DELETE" })
}
