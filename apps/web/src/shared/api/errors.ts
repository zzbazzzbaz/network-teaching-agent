import { ApiError } from "./client"

type StatusMessages = Partial<Record<number, string>>

/**
 * 把 API / 网络错误统一成面向学生的文案。
 * 状态码文案优先，其次使用后端 message，最后回退到页面自己的兜底。
 */
export function humanizeApiError(
  error: unknown,
  fallback: string,
  statusMessages?: StatusMessages,
): string {
  if (error instanceof ApiError) {
    const mapped = statusMessages?.[error.status]
    if (mapped) return mapped
    if (error.message) return error.message
    return fallback
  }
  if (error instanceof TypeError) return "无法连接服务器，请确认服务已启动"
  if (error instanceof Error && error.message) return error.message
  return fallback
}
