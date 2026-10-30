import { humanizeApiError } from "@/shared/api/errors"
import type { SandboxStatus } from "@/shared/api/types"

export type SandboxDisplayStatus = SandboxStatus | "idle"

export const STATUS_LABEL: Record<SandboxDisplayStatus, string> = {
  idle: "尚未启动",
  running: "运行中",
  paused: "已暂停",
  stopping: "销毁中",
}

export const STATUS_DOT: Record<SandboxDisplayStatus, string> = {
  idle: "bg-line-strong",
  running: "bg-link",
  paused: "bg-signal",
  stopping: "bg-signal animate-pulse",
}

export const STATUS_HINT: Record<SandboxDisplayStatus, string | null> = {
  idle: "无活动沙盒",
  running: null,
  paused: "文件保留",
  stopping: "正在清理",
}

export function sandboxErrorMessage(error: unknown, fallback: string): string {
  return humanizeApiError(error, fallback, {
    409: "沙盒正在销毁，请稍后重试",
    503: "沙盒服务暂不可用，请稍后重试",
  })
}
