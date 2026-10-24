import { expect, test } from "@playwright/test";

import { createNewSession, login, stopSandbox } from "./helpers";

test.describe("ask_human 中断", () => {
  test.afterEach(async ({ page }) => {
    await stopSandbox(page);
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
    await createNewSession(page);
  });

  test("中断卡片渲染选项，作答后 agent 继续运行", async ({ page }) => {
    await page
      .getByTestId("composer-input")
      .fill("请直接调用 ask_human 工具考我一题，不要解释。");
    await page.getByTestId("composer-send").click();

    const card = page.getByTestId("ask-human-card");
    await expect(card).toBeVisible({ timeout: 150_000 });

    await expect(page.getByTestId("ask-human-query")).not.toHaveText("");

    const options = page.getByTestId("ask-human-option");
    await expect(options.first()).toBeVisible();
    expect(await options.count()).toBeGreaterThanOrEqual(2);

    await options.first().click();
    await expect(page.getByTestId("ask-human-submitting")).toBeVisible();

    await expect(card).toBeHidden({ timeout: 150_000 });

    // 恢复后 agent 继续输出，且输入框重新出现
    await expect(page.getByTestId("composer-input")).toBeVisible();
    await expect(page.getByTestId("message-assistant").last()).not.toHaveText(
      "",
      { timeout: 150_000 },
    );

    // 中断已消费，刷新后不应再次停留
    await page.reload();
    await expect(page.getByTestId("ask-human-card")).toBeHidden();
    await expect(page.getByTestId("composer-input")).toBeVisible();
  });
});
