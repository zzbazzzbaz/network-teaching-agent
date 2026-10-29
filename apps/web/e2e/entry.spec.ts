import { expect, test } from "@playwright/test"

test.describe("entry", () => {
  test("登录页在桌面和手机宽度下无横向溢出", async ({ page }) => {
    for (const size of [
      { width: 1440, height: 900 },
      { width: 390, height: 844 },
      { width: 320, height: 667 },
    ]) {
      await page.setViewportSize(size)
      await page.goto("/login", { waitUntil: "networkidle" })
      await expect(
        page.getByRole("heading", { name: "登录课程空间" }),
      ).toBeVisible()
      const layout = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        scrollHeight: document.documentElement.scrollHeight,
        clientHeight: document.documentElement.clientHeight,
      }))
      expect(layout.scrollWidth).toBe(layout.clientWidth)
      expect(layout.scrollHeight).toBe(layout.clientHeight)
    }
  })

  test("未登录访问深链会带 redirect 回到登录页", async ({ page }) => {
    const sessionId = "00000000-0000-4000-8000-000000000000"
    await page.goto(`/learn/${sessionId}?panel=questions`, {
      waitUntil: "networkidle",
    })
    await expect(page).toHaveURL(/\/login\?redirect=/)
    await expect(
      page.getByRole("heading", { name: "登录课程空间" }),
    ).toBeVisible()
  })
})
