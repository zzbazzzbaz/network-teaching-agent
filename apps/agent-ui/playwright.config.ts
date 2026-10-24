import { defineConfig, devices } from "@playwright/test";

// 前端 E2E 对接真实后端：API 与 Agent 需要提前启动，本配置只负责拉起前端 dev server。
const APP_URL = process.env.E2E_APP_URL ?? "http://localhost:5174";
const APP_PORT = new URL(APP_URL).port || "5174";
const AGENT_URL = process.env.E2E_AGENT_URL ?? "http://127.0.0.1:2024";
const API_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";

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
      // 只启动前端；代理目标指向已经运行的真实 API / Agent。
      command: `PORT=${APP_PORT} AGENT_URL=${AGENT_URL} API_URL=${API_URL} npm run dev`,
      url: APP_URL,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
