import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"

import { ApiError } from "@/shared/api/client"
import type { Sandbox } from "@/shared/api/types"

import {
  destroySandbox,
  ensureSandbox,
  fetchSandbox,
  heartbeatSandbox,
  pauseSandbox,
} from "./api"

export const STOPPING_POLL_MS = 10_000

export const sandboxKeys = {
  detail: ["sandbox"] as const,
}

/** 404 表示还没有沙盒，是正常空闲状态。 */
async function fetchSandboxOrNull(): Promise<Sandbox | null> {
  try {
    return await fetchSandbox()
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

export function useSandbox() {
  return useQuery({
    queryKey: sandboxKeys.detail,
    queryFn: fetchSandboxOrNull,
    refetchInterval: (query) =>
      query.state.data?.status === "stopping" ? STOPPING_POLL_MS : false,
  })
}

export function useStartSandbox() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ensureSandbox,
    onSuccess: (sandbox) => {
      queryClient.setQueryData<Sandbox | null>(sandboxKeys.detail, sandbox)
    },
  })
}

export function usePauseSandbox() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: pauseSandbox,
    onSuccess: (sandbox) => {
      queryClient.setQueryData<Sandbox | null>(sandboxKeys.detail, sandbox)
    },
  })
}

export function useHeartbeatSandbox() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: heartbeatSandbox,
    onSuccess: (sandbox) => {
      queryClient.setQueryData<Sandbox | null>(sandboxKeys.detail, (current) =>
        current?.status === "running" ? sandbox : (current ?? null),
      )
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 404) {
        queryClient.setQueryData<Sandbox | null>(sandboxKeys.detail, null)
      }
    },
  })
}

export function useDestroySandbox() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: destroySandbox,
    onSuccess: (result) => {
      if (result?.status === "stopping") {
        const current = queryClient.getQueryData<Sandbox | null>(
          sandboxKeys.detail,
        )
        if (current) {
          const stopping: Sandbox = {
            ...current,
            status: "stopping",
            vscode_url: null,
            ttyd_url: null,
          }
          queryClient.setQueryData<Sandbox | null>(
            sandboxKeys.detail,
            stopping,
          )
        } else {
          void queryClient.invalidateQueries({ queryKey: sandboxKeys.detail })
        }
        return
      }
      queryClient.setQueryData<Sandbox | null>(sandboxKeys.detail, null)
    },
  })
}
