import { expect, test } from "@playwright/test";

import { login, logout } from "./helpers";

test.describe("登录", () => {
  test("未登录访问首页会跳转到登录页", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByTestId("login-page")).toBeVisible();
    await expect(page.getByTestId("login-submit")).toBeVisible();
  });

  test("密码错误时停留在登录页并提示", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill("e2e_student");
    await page.getByTestId("login-password").fill("wrong-password");
    await page.getByTestId("login-submit").click();

    await expect(page.getByTestId("login-error")).toHaveText("用户名或密码错误");
    await expect(page.getByTestId("login-page")).toBeVisible();
  });

  test("登录后显示会话列表，退出后回到登录页", async ({ page }) => {
    await login(page);
    await expect(page.getByTestId("current-user")).toHaveText("e2e_student");
    await logout(page);
    await expect(page).toHaveURL(/\/login$/);
  });
});
