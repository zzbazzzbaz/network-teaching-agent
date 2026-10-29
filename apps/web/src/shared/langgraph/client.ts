/** LangGraph Server 聊天运行时传输：带登录态的 Client。 */

import { Client } from "@langchain/langgraph-sdk"

import { authedFetch } from "@/shared/api/client"
import { getAccessToken } from "@/shared/auth/session"

export const LANGGRAPH_BASE_URL = new URL("/agent", window.location.origin)
  .toString()
  .replace(/\/$/, "")

/** SDK 的普通请求走 authedFetch（401 自动续期）；流式请求由 onRequest 注入 token。 */
export function createLangGraphClient(): Client {
  return new Client({
    apiUrl: LANGGRAPH_BASE_URL,
    apiKey: null,
    onRequest: (_url, init) => {
      const token = getAccessToken()
      if (!token) return init
      const headers = new Headers(init.headers)
      headers.set("Authorization", `Bearer ${token}`)
      return { ...init, headers }
    },
    callerOptions: { fetch: authedFetch },
  })
}
