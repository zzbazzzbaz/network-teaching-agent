import { expect, test } from "@playwright/test";

import { createNewSession, login, stopSandbox } from "./helpers";

test.describe("ask_student 中断", () => {
  test.afterEach(async ({ page }) => {
    await stopSandbox(page);
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
    await createNewSession(page);
  });

  test("单选：渲染选项，作答后 agent 继续运行", async ({ page }) => {
    const ensureCalls: string[] = [];
    page.on("request", (request) => {
      if (
        request.method() === "POST" &&
        new URL(request.url()).pathname === "/api/v1/sandbox"
      ) {
        ensureCalls.push(request.url());
      }
    });

    await page
      .getByTestId("composer-input")
      .fill(
        "请只调用 ask_student 工具，用 single_choice 模式考我一道 TTL 相关的小题，2 个选项，不要解释。",
      );
    await page.getByTestId("composer-send").click();

    const card = page.getByTestId("ask-student-card");
    await expect(card).toBeVisible({ timeout: 150_000 });

    await expect(page.getByTestId("ask-student-query")).not.toHaveText("");

    const options = page.getByTestId("ask-student-option");
    await expect(options.first()).toBeVisible();
    expect(await options.count()).toBeGreaterThanOrEqual(2);

    await options.first().click();
    await expect(page.getByTestId("ask-student-submitting")).toBeVisible();

    await expect(card).toBeHidden({ timeout: 150_000 });

    // 恢复后 agent 继续输出，且输入框重新出现
    await expect(page.getByTestId("composer-input")).toBeVisible();
    await expect(page.getByTestId("message-assistant").last()).not.toHaveText(
      "",
      { timeout: 150_000 },
    );

    // 中断已消费，刷新后不应再次停留
    await page.reload();
    await expect(page.getByTestId("ask-student-card")).toBeHidden();
    await expect(page.getByTestId("composer-input")).toBeVisible();
    expect(ensureCalls).toHaveLength(0);
  });

  test("简答：空答案不可提交，输入后提交并继续", async ({ page }) => {
    await page
      .getByTestId("composer-input")
      .fill(
        "请只调用 ask_student 工具，用 short_answer 模式考我一道 traceroute 的小题，不要解释。",
      );
    await page.getByTestId("composer-send").click();

    const card = page.getByTestId("ask-student-card");
    await expect(card).toBeVisible({ timeout: 150_000 });

    const answer = page.getByTestId("ask-student-answer");
    const submit = page.getByTestId("ask-student-submit");
    await expect(answer).toBeVisible();
    await expect(submit).toBeDisabled();

    await answer.fill("因为发送方需要知道是哪一个原始探测包出错了。");
    await expect(submit).toBeEnabled();
    await submit.click();

    await expect(page.getByTestId("ask-student-submitting")).toBeVisible();
    await expect(card).toBeHidden({ timeout: 150_000 });
    await expect(page.getByTestId("composer-input")).toBeVisible();
  });

  test("题干 Markdown 中的 Mermaid 渲染为图", async ({ page }) => {
    await page
      .getByTestId("composer-input")
      .fill(
        [
          "请只调用 ask_student 工具，用 short_answer 模式，问一个 traceroute 问题。",
          "题干必须包含下面这个 Mermaid 代码块，不要改写，也不要解释：",
          "```mermaid",
          "graph LR",
          "  A[你的电脑] --> B[路由器 1]",
          "  B --> C[目标]",
          "```",
        ].join("\n"),
      );
    await page.getByTestId("composer-send").click();

    await expect(page.getByTestId("ask-student-card")).toBeVisible({
      timeout: 150_000,
    });
    await expect(page.getByTestId("ask-student-query")).not.toHaveText("");
    await expect(page.getByTestId("mermaid-diagram").first()).toBeVisible({
      timeout: 60_000,
    });
  });
});
