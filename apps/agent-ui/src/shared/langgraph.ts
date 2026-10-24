/** LangGraph Server 传输：带登录态的 Client + 运行时线程创建/删除。 */

import { Client } from "@langchain/langgraph-sdk";

import { ApiError, authedFetch } from "./http";
import { getAccessToken } from "./session";

export const LANGGRAPH_BASE_URL = new URL("/agent", window.location.origin)
  .toString()
  .replace(/\/$/, "");

/** SDK 的普通请求走 authedFetch（401 自动续期）；流式请求由 onRequest 注入 token。 */
export function createLangGraphClient(): Client {
  return new Client({
    apiUrl: LANGGRAPH_BASE_URL,
    apiKey: null,
    onRequest: (_url, init) => {
      const token = getAccessToken();
      if (!token) return init;
      const headers = new Headers(init.headers);
      headers.set("Authorization", `Bearer ${token}`);
      return { ...init, headers };
    },
    callerOptions: { fetch: authedFetch },
  });
}

async function ensureOk(response: Response, message: string): Promise<void> {
  if (response.ok) return;
  let detail = message;
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string" && data.detail) detail = data.detail;
  } catch {
    // 忽略非 JSON 错误体
  }
  throw new ApiError(response.status, detail);
}

/** 用平台 session_id 作为 LangGraph thread_id 补建线程（幂等）。 */
export async function ensureLangGraphThread(threadId: string): Promise<void> {
  const response = await authedFetch(`${LANGGRAPH_BASE_URL}/threads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, if_exists: "do_nothing" }),
  });
  await ensureOk(response, "创建对话线程失败");
}

/** 删除运行时线程；不存在视为已删除。 */
export async function deleteLangGraphThread(threadId: string): Promise<void> {
  const response = await authedFetch(`${LANGGRAPH_BASE_URL}/threads/${threadId}`, {
    method: "DELETE",
  });
  if (response.status === 404) return;
  await ensureOk(response, "删除对话线程失败");
}
