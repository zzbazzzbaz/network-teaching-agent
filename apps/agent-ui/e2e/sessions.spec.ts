import { expect, test } from "@playwright/test";

import { createNewSession, login, logout, OTHER_PASSWORD, OTHER_USERNAME } from "./helpers";

test.describe("会话列表", () => {
  test("新建会话、重命名、刷新后仍保留", async ({ page }) => {
    await login(page);
    await createNewSession(page);

    const active = page.locator(".session-item-active");
    await expect(active).toContainText("新会话");

    await active.getByTestId("session-rename").click();
    const input = page.getByTestId("session-rename-input");
    await input.fill("TCP 三次握手");
    await page.getByTestId("session-rename-save").click();

    await expect(active).toContainText("TCP 三次握手");
    await page.reload();
    await expect(page.locator(".session-item-active")).toContainText("TCP 三次握手");
  });

  test("删除会话后从列表消失", async ({ page }) => {
    await login(page);
    await createNewSession(page);

    const active = page.locator(".session-item-active");
    const sessionId = await active.getAttribute("data-session-id");
    await active.getByTestId("session-rename").click();
    await page.getByTestId("session-rename-input").fill("待删除会话");
    await page.getByTestId("session-rename-save").click();
    await expect(active).toContainText("待删除会话");

    page.once("dialog", (dialog) => void dialog.accept());
    await active.getByTestId("session-delete").click();

    await expect(
      page.locator(`[data-testid="session-item"][data-session-id="${sessionId ?? ""}"]`),
    ).toHaveCount(0);
  });

  test("其他用户打开会话链接时被拒绝", async ({ page }) => {
    await login(page);
    await createNewSession(page);
    const sessionUrl = page.url();

    await logout(page);
    await login(page, OTHER_USERNAME, OTHER_PASSWORD);
    await page.goto(sessionUrl);

    await expect(page.getByTestId("chat-error")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("chat-error")).toContainText("会话不存在或无权访问");
    await expect(page.getByTestId("composer-input")).toHaveCount(0);
  });
});
