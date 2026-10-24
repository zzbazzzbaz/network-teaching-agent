import { randomUUID } from "node:crypto";

import { expect, test, type APIRequestContext } from "@playwright/test";

import {
  OTHER_PASSWORD,
  OTHER_USERNAME,
  STUDENT_PASSWORD,
  STUDENT_USERNAME,
} from "./helpers";

async function apiLogin(
  request: APIRequestContext,
  username: string,
  password: string,
): Promise<string> {
  const response = await request.post("/api/v1/auth/login", {
    data: { username, password },
  });
  expect(response.ok()).toBeTruthy();
  const data = (await response.json()) as { access_token: string };
  return data.access_token;
}

function bearer(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

test.describe("Agent 资源隔离", () => {
  test("未登录访问 LangGraph 返回 401", async ({ request }) => {
    const response = await request.get("/agent/threads");
    expect(response.status()).toBe(401);
  });

  test("用户只能读取、搜索、更新、删除自己的线程", async ({ request }) => {
    const aliceToken = await apiLogin(request, STUDENT_USERNAME, STUDENT_PASSWORD);
    const bobToken = await apiLogin(request, OTHER_USERNAME, OTHER_PASSWORD);
    const threadId = randomUUID();

    const created = await request.post("/agent/threads", {
      headers: bearer(aliceToken),
      data: { thread_id: threadId, if_exists: "do_nothing" },
    });
    expect(created.status()).toBe(200);

    const aliceRead = await request.get(`/agent/threads/${threadId}/state`, {
      headers: bearer(aliceToken),
    });
    expect(aliceRead.status()).toBe(200);

    // owner 由服务端钉死：A 自己改 metadata.owner 也不能把线程转走。
    const aliceUpdate = await request.patch(`/agent/threads/${threadId}`, {
      headers: bearer(aliceToken),
      data: { metadata: { owner: "someone-else" } },
    });
    expect(aliceUpdate.status()).toBe(200);
    expect((await aliceUpdate.json()) as { metadata: { owner: string } }).toMatchObject({
      metadata: { owner: expect.any(String) },
    });

    const bobRead = await request.get(`/agent/threads/${threadId}/state`, {
      headers: bearer(bobToken),
    });
    expect([403, 404]).toContain(bobRead.status());

    // B 不能通过 if_exists=do_nothing 探测或接管 A 的线程。
    const bobCreate = await request.post("/agent/threads", {
      headers: bearer(bobToken),
      data: { thread_id: threadId, if_exists: "do_nothing" },
    });
    expect([403, 409]).toContain(bobCreate.status());

    const assistants = await request.post("/agent/assistants/search", {
      headers: bearer(aliceToken),
      data: { limit: 10 },
    });
    expect(assistants.status()).toBe(403);

    const aliceSearch = await request.post("/agent/threads/search", {
      headers: bearer(aliceToken),
      data: { limit: 100 },
    });
    expect(aliceSearch.status()).toBe(200);
    const aliceThreads = (await aliceSearch.json()) as Array<{ thread_id: string }>;
    expect(aliceThreads.some((thread) => thread.thread_id === threadId)).toBeTruthy();

    const bobSearch = await request.post("/agent/threads/search", {
      headers: bearer(bobToken),
      data: { limit: 100 },
    });
    expect(bobSearch.status()).toBe(200);
    const bobThreads = (await bobSearch.json()) as Array<{ thread_id: string }>;
    expect(bobThreads.some((thread) => thread.thread_id === threadId)).toBeFalsy();

    const bobUpdate = await request.patch(`/agent/threads/${threadId}`, {
      headers: bearer(bobToken),
      data: { metadata: { title: "hijack" } },
    });
    expect([403, 404]).toContain(bobUpdate.status());

    const bobRun = await request.post(`/agent/threads/${threadId}/runs`, {
      headers: bearer(bobToken),
      data: { assistant_id: "exp_agent", input: { messages: [] } },
    });
    expect([403, 404]).toContain(bobRun.status());

    const bobDelete = await request.delete(`/agent/threads/${threadId}`, {
      headers: bearer(bobToken),
    });
    expect([403, 404]).toContain(bobDelete.status());

    const aliceDelete = await request.delete(`/agent/threads/${threadId}`, {
      headers: bearer(aliceToken),
    });
    expect(aliceDelete.status()).toBe(204);

    const afterDelete = await request.get(`/agent/threads/${threadId}/state`, {
      headers: bearer(aliceToken),
    });
    expect(afterDelete.status()).toBe(404);
  });
});
