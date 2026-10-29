import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"
import { defineConfig } from "vite"

import { requireEnv } from "./env.ts"

const AGENT_URL = requireEnv("AGENT_URL")
const API_URL = requireEnv("API_URL")
const DEV_PORT = 5173

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    port: DEV_PORT,
    strictPort: true,
    proxy: {
      "/api": {
        target: API_URL,
        changeOrigin: true,
      },
      "/agent": {
        target: AGENT_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent/, ""),
      },
    },
  },
})
