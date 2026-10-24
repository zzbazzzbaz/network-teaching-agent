import { defineConfig, devices } from "@playwright/test";

import { requireEnv } from "./env.ts";

// 前端 E2E 对接真实后端：API 与 Agent 需要提前启动，本配置只负责拉起前端 dev server。
const APP_URL = requireEnv("E2E_APP_URL");
const APP_PORT = new URL(APP_URL).port;
if (!APP_PORT) {
  throw new Error(`E2E_APP_URL 必须包含端口，当前值：${APP_URL}`);
}

export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 60_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: APP_URL,
    locale: "zh-CN",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // 只启动前端；代理目标由 apps/.env 中的 AGENT_URL / API_URL 决定。
      command: `npm run dev -- --port ${APP_PORT}`,
      url: APP_URL,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
