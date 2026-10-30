import {
  infiniteQueryOptions,
  queryOptions,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"

import type { AgentId, Mode, Session } from "@/shared/api/types"

import {
  createSession,
  deleteSession,
  getSession,
  listSessions,
  renameSession,
} from "./api"
import { MODES } from "./model"

export const sessionKeys = {
  all: ["sessions"] as const,
  list: (agentId: AgentId) => ["sessions", agentId] as const,
  detail: (sessionId: string) => ["session", sessionId] as const,
}

export function sessionsQueryOptions(agentId: AgentId) {
  return infiniteQueryOptions({
    queryKey: sessionKeys.list(agentId),
    queryFn: ({ pageParam }) =>
      listSessions({ agentId, limit: 20, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const next = lastPage.offset + lastPage.items.length
      return next < lastPage.total ? next : undefined
    },
  })
}

export function sessionQueryOptions(sessionId: string) {
  return queryOptions({
    queryKey: sessionKeys.detail(sessionId),
    queryFn: () => getSession(sessionId),
    staleTime: 30_000,
  })
}

export function useSessions(agentId: AgentId) {
  return useInfiniteQuery(sessionsQueryOptions(agentId))
}

export function useCreateSession(mode: Mode) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input?: { title?: string }) =>
      createSession(MODES[mode].agentId, input?.title ?? ""),
    onSuccess: (session) => {
      queryClient.setQueryData(sessionKeys.detail(session.session_id), session)
      void queryClient.invalidateQueries({
        queryKey: sessionKeys.list(MODES[mode].agentId),
      })
    },
  })
}

export function useRenameSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      renameSession(sessionId, title),
    onSuccess: (session) => {
      queryClient.setQueryData(sessionKeys.detail(session.session_id), session)
      void queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}

export function useDeleteSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (session: Session) => deleteSession(session.session_id),
    onSuccess: (_data, session) => {
      queryClient.removeQueries({
        queryKey: sessionKeys.detail(session.session_id),
      })
      // 先从无限列表缓存里移除，避免删除当前会话后模式首页仍把已删会话
      // 当作“最近会话”再次跳转，形成 404。
      queryClient.setQueryData(
        sessionKeys.list(session.agent_id),
        (previous: unknown) => {
          if (!previous || typeof previous !== "object") return previous
          const data = previous as {
            pages?: {
              items?: { session_id: string }[]
              total?: number
              limit?: number
              offset?: number
            }[]
            pageParams?: unknown[]
          }
          if (!Array.isArray(data.pages)) return previous
          return {
            ...data,
            pages: data.pages.map((page) => ({
              ...page,
              items: (page.items ?? []).filter(
                (item) => item.session_id !== session.session_id,
              ),
              total: Math.max(0, (page.total ?? 1) - 1),
            })),
          }
        },
      )
      void queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}
