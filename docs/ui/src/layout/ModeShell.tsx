import { useEffect, useState } from "react"
import { Outlet } from "react-router-dom"

import { Sidebar } from "@/layout/Sidebar"
import { ShellContext } from "@/layout/shell"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
} from "@/components/ui/sheet"
import type { Mode } from "@/lib/mock"
import { useMediaQuery } from "@/lib/hooks"
import { cn } from "@/lib/utils"

export function ModeShell({ mode }: { mode: Mode }) {
  const [navOpen, setNavOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false
    return window.localStorage.getItem("ui1.sidebar") === "collapsed"
  })
  const isWide = useMediaQuery("(min-width: 1024px)")

  useEffect(() => {
    if (isWide) setNavOpen(false)
  }, [isWide])

  useEffect(() => {
    window.localStorage.setItem(
      "ui1.sidebar",
      collapsed ? "collapsed" : "expanded",
    )
  }, [collapsed])

  return (
    <ShellContext.Provider
      value={{
        mode,
        openNav: () => setNavOpen(true),
        closeNav: () => setNavOpen(false),
      }}
    >
      <div className="min-h-dvh bg-surface">
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-line bg-paper transition-[width] duration-200 lg:flex",
            collapsed ? "w-[72px]" : "w-[284px]",
          )}
        >
          <Sidebar
            mode={mode}
            collapsed={collapsed}
            onToggleCollapse={() => setCollapsed((value) => !value)}
          />
        </aside>

        <Sheet open={navOpen} onOpenChange={setNavOpen}>
          <SheetContent
            side="left"
            className="w-[88vw] max-w-[320px] border-r border-line bg-paper p-0"
          >
            <SheetTitle className="sr-only">会话列表</SheetTitle>
            <SheetDescription className="sr-only">
              按时间排列的学习与实验会话
            </SheetDescription>
            <Sidebar mode={mode} onNavigate={() => setNavOpen(false)} />
          </SheetContent>
        </Sheet>

        <div
          className={cn(
            "transition-[padding] duration-200",
            collapsed ? "lg:pl-[72px]" : "lg:pl-[284px]",
          )}
        >
          <Outlet />
        </div>
      </div>
    </ShellContext.Provider>
  )
}
