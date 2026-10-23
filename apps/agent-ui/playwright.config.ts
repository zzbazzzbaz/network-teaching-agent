import { defineConfig, devices } from "@playwright/test";

const APP_URL = "http://localhost:5173";
const AGENT_URL = "http://127.0.0.1:2024";

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
      command: "cd ../agent && uv run langgraph dev --port 2024 --no-browser",
      url: `${AGENT_URL}/ok`,
      reuseExistingServer: true,
      timeout: 180_000,
      stdout: "ignore",
      stderr: "pipe",
    },
    {
      command: "npm run dev",
      url: APP_URL,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
