import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "@fontsource/ibm-plex-sans/400.css"
import "@fontsource/ibm-plex-sans/500.css"
import "@fontsource/ibm-plex-sans/600.css"
import "@fontsource/ibm-plex-mono/400.css"
import "@fontsource/ibm-plex-mono/500.css"
import "./styles.css"

import { AppProviders } from "./providers/AppProviders"
import { router } from "./router"
import { RouterProvider } from "@tanstack/react-router"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
)
