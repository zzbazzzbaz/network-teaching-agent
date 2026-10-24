import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import path from "node:path";

import { requireEnv } from "./env.ts";

const AGENT_URL = requireEnv("AGENT_URL");
const API_URL = requireEnv("API_URL");
const PORT = Number(requireEnv("UI_PORT"));

if (!Number.isInteger(PORT) || PORT <= 0) {
  throw new Error(`UI_PORT 必须是正整数，当前值：${requireEnv("UI_PORT")}`);
}

export default defineConfig({
  plugins: [
    tanstackRouter({ target: "react", autoCodeSplitting: true }),
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    port: PORT,
    strictPort: true,
    proxy: {
      "/api": {
        target: API_URL,
        changeOrigin: true,
      },
      "/agent": {
        target: AGENT_URL,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/agent/, ""),
      },
    },
  },
});
