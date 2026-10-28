// Exposes React component/profiling tools to chrome-devtools-mcp. Must be
// imported before react-dom so the DevTools hook is installed in time.
import "react-devtools-cdt-mcp/register";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";

import { AuthProvider } from "@/features/auth";
import { router } from "./router";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);
