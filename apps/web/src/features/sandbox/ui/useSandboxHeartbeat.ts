import { useEffect, useRef } from "react"

import type { Sandbox } from "@/shared/api/types"

import { useHeartbeatSandbox } from "../queries"

/** 面板挂载且沙盒运行中时续期；卸载或暂停后立即停止。 */
export function useSandboxHeartbeat(sandbox: Sandbox | null) {
  const { mutate: sendHeartbeat } = useHeartbeatSandbox()
  const inFlight = useRef(false)
  const status = sandbox?.status
  const seconds = sandbox?.heartbeat_seconds

  useEffect(() => {
    if (status !== "running" || !seconds) return
    const interval = Math.max(30, seconds) * 1_000
    const timer = window.setInterval(() => {
      if (inFlight.current) return
      inFlight.current = true
      sendHeartbeat(undefined, {
        onSettled: () => {
          inFlight.current = false
        },
      })
    }, interval)
    return () => window.clearInterval(timer)
  }, [seconds, sendHeartbeat, status])
}
