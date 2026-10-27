import { expect, test } from "@playwright/test";

import { createNewSession, login, stopSandbox } from "./helpers";

test.describe("基础聊天", () => {
  test.afterEach(async ({ page }) => {
    await stopSandbox(page);
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
    await createNewSession(page);
  });

  test("初始为空态，输入框为空时不能发送", async ({ page }) => {
    await expect(page.getByTestId("empty-state")).toBeVisible();
    await expect(page.getByTestId("composer-input")).toBeVisible();
    await expect(page.getByTestId("composer-send")).toBeDisabled();
    await expect(page.getByTestId("ask-student-card")).toBeHidden();
  });

  test("发送消息后收到流式回复，URL 带上 threadId，刷新可恢复", async ({
    page,
  }) => {
    const ensureCalls: string[] = [];
    page.on("request", (request) => {
      if (
        request.method() === "POST" &&
        new URL(request.url()).pathname === "/api/v1/sandbox"
      ) {
        ensureCalls.push(request.url());
      }
    });

    const input = page.getByTestId("composer-input");
    await input.fill("用一句话解释 TCP 三次握手的目的是什么。");
    await page.getByTestId("composer-send").click();

    await expect(page.getByTestId("message-user")).toHaveCount(1);
    await expect(page).toHaveURL(/threadId=/, { timeout: 30_000 });

    const reply = page.getByTestId("message-assistant").last();
    await expect(reply).toBeVisible();
    await expect(reply).not.toHaveText("", { timeout: 150_000 });

    const url = page.url();
    await page.goto(url);

    await expect(page.getByTestId("message-user")).toHaveCount(1);
    await expect(page.getByTestId("message-assistant").last()).not.toHaveText(
      "",
      { timeout: 60_000 },
    );
    await expect(page.getByTestId("empty-state")).toBeHidden();
    expect(ensureCalls).toHaveLength(0);
  });
});
