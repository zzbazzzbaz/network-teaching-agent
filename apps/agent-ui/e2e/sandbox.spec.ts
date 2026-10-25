import { expect, test } from "@playwright/test";

import { login } from "./helpers";

test.describe("账户沙箱", () => {
  test("启动、暂停、恢复并销毁", async ({ page }) => {
    await login(page);
    await expect(page.getByTestId("sandbox-bar")).toBeVisible();

    const start = page.getByTestId("sandbox-start");
    if (await start.isVisible().catch(() => false)) {
      await start.click();
    } else {
      const retry = page.getByTestId("sandbox-retry");
      if (await retry.isVisible().catch(() => false)) {
        await retry.click();
      }
    }

    const vscode = page.getByTestId("sandbox-vscode");
    const ttyd = page.getByTestId("sandbox-ttyd");
    await expect(vscode).toBeVisible({ timeout: 180_000 });
    await expect(ttyd).toBeVisible();

    const vscodeUrl = await vscode.getAttribute("href");
    const ttydUrl = await ttyd.getAttribute("href");
    expect(vscodeUrl).toMatch(/^https:\/\/9000-/);
    expect(ttydUrl).toMatch(/^https:\/\/9000-/);

    expect((await page.request.get(vscodeUrl!)).status()).toBe(200);
    expect((await page.request.get(ttydUrl!)).status()).toBe(200);

    const sandboxId = await page.getByTestId("sandbox-bar").getAttribute("data-sandbox-id");

    await page.getByTestId("sandbox-pause").click();
    await expect(page.getByTestId("sandbox-resume")).toBeVisible({ timeout: 60_000 });
    await expect(vscode).toBeHidden();
    await expect
      .poll(async () => (await page.request.get(vscodeUrl!)).status(), {
        timeout: 60_000,
      })
      .toBe(404);

    await page.getByTestId("sandbox-resume").click();
    await expect(vscode).toBeVisible({ timeout: 120_000 });
    expect(await page.getByTestId("sandbox-bar").getAttribute("data-sandbox-id")).toBe(
      sandboxId,
    );
    await expect
      .poll(async () => (await page.request.get(vscodeUrl!)).status(), {
        timeout: 60_000,
      })
      .toBe(200);

    const popupPromise = page.waitForEvent("popup");
    await vscode.click();
    const popup = await popupPromise;
    await popup.waitForURL(/^https:\/\/9000-/, { timeout: 60_000 });
    await popup.close();

    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByTestId("sandbox-stop").click();
    await expect(page.getByTestId("sandbox-start")).toBeVisible({
      timeout: 60_000,
    });
  });
});
