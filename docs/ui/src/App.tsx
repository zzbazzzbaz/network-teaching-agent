import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ModeShell } from "@/layout/ModeShell"
import { StoreProvider } from "@/lib/store"
import { LoginPage } from "@/pages/LoginPage"
import { ModeEntry } from "@/pages/ModeEntry"
import { SessionPage } from "@/pages/SessionPage"
import { StyleGuidePage } from "@/pages/StyleGuidePage"

export default function App() {
  return (
    <StoreProvider>
      <TooltipProvider>
        <BrowserRouter>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:border focus:border-line focus:bg-surface focus:px-3 focus:py-2 focus:text-[13px] focus:shadow-md"
          >
            跳到主要内容
          </a>

          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<Navigate to="/learn" replace />} />
            <Route path="/styleguide" element={<StyleGuidePage />} />

            <Route element={<ModeShell mode="learn" />}>
              <Route path="/learn" element={<ModeEntry mode="learn" />} />
              <Route
                path="/learn/:sessionId"
                element={<SessionPage mode="learn" />}
              />
            </Route>

            <Route element={<ModeShell mode="lab" />}>
              <Route path="/lab" element={<ModeEntry mode="lab" />} />
              <Route
                path="/lab/:sessionId"
                element={<SessionPage mode="lab" />}
              />
            </Route>

            <Route path="*" element={<Navigate to="/learn" replace />} />
          </Routes>

          <Toaster />
        </BrowserRouter>
      </TooltipProvider>
    </StoreProvider>
  )
}
