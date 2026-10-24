import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import path from "node:path";

const AGENT_URL = process.env.AGENT_URL ?? "http://127.0.0.1:2024";
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const PORT = Number(process.env.PORT ?? 5173);

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
