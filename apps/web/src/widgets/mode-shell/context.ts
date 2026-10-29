import { createContext, useContext } from "react"

import type { Mode } from "@/shared/api/types"

export const ShellContext = createContext<{
  mode: Mode
  openNav: () => void
  closeNav: () => void
} | null>(null)

export function useShell() {
  const context = useContext(ShellContext)
  if (!context) throw new Error("useShell must be used inside ModeShell")
  return context
}
