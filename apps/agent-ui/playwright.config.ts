import { defineConfig, devices } from "@playwright/test";

const APP_URL = "http://localhost:5174";
const AGENT_URL = "http://127.0.0.1:2025";
const API_URL = "http://127.0.0.1:8001";

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
      command: "cd ../api && E2E_API_PORT=8001 uv run python scripts/e2e_server.py",
      url: `${API_URL}/health`,
      reuseExistingServer: true,
      timeout: 180_000,
      stdout: "ignore",
      stderr: "pipe",
    },
    {
      command:
        "cd ../agent && JWKS_URL_OVERRIDE=http://127.0.0.1:8001/.well-known/jwks.json uv run langgraph dev --port 2025 --no-browser",
      url: `${AGENT_URL}/ok`,
      reuseExistingServer: true,
      timeout: 180_000,
      stdout: "ignore",
      stderr: "pipe",
    },
    {
      command: "PORT=5174 AGENT_URL=http://127.0.0.1:2025 API_URL=http://127.0.0.1:8001 npm run dev",
      url: APP_URL,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
