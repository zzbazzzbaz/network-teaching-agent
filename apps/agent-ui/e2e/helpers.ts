import { expect, type Page } from "@playwright/test";

import { requireEnv } from "../env.ts";

export const STUDENT_USERNAME = requireEnv("E2E_STUDENT_USERNAME");
export const STUDENT_PASSWORD = requireEnv("E2E_STUDENT_PASSWORD");
export const OTHER_USERNAME = requireEnv("E2E_OTHER_USERNAME");
export const OTHER_PASSWORD = requireEnv("E2E_OTHER_PASSWORD");

export async function login(
  page: Page,
  username: string = STUDENT_USERNAME,
  password: string = STUDENT_PASSWORD,
): Promise<void> {
  await page.goto("/login");
  await page.getByTestId("login-username").fill(username);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("session-sidebar")).toBeVisible();
  await expect(page.getByTestId("login-page")).toBeHidden();
}

export async function logout(page: Page): Promise<void> {
  await page.getByTestId("logout-button").click();
  await expect(page.getByTestId("login-page")).toBeVisible();
}

export async function createNewSession(page: Page): Promise<void> {
  const before = new URL(page.url()).searchParams.get("threadId");
  await page.getByTestId("session-new").click();

  // 新建是异步的：必须等到 URL 换成一个新的 threadId，不能只看“已有 threadId”。
  await expect
    .poll(() => new URL(page.url()).searchParams.get("threadId"), {
      timeout: 30_000,
    })
    .not.toBe(before);

  const threadId = new URL(page.url()).searchParams.get("threadId");
  await expect(page.getByTestId("empty-state")).toBeVisible({ timeout: 30_000 });

  // 等待侧栏把 active 标记切到当前 URL 对应的会话，避免测试点到上一个会话。
  await expect(
    page.locator(
      `[data-testid="session-item"][data-session-id="${threadId ?? ""}"]`,
    ),
  ).toHaveClass(/session-item-active/, { timeout: 30_000 });
}
