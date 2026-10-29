import type { ReactNode } from "react"

import { cn } from "@/shared/lib/utils"

/** Shared horizontal rhythm for every workspace page. */
export const workspaceContentClass =
  "mx-auto w-full max-w-[1080px] px-4 lg:px-8 xl:px-10"

export function WorkspaceHeader({
  title,
  actions,
  className,
}: {
  title: string
  actions?: ReactNode
  className?: string
}) {
  return (
    <header
      className={cn(
        "hidden h-14 shrink-0 border-b border-line bg-surface lg:block",
        className,
      )}
    >
      <div className={cn("flex h-full items-center gap-3", workspaceContentClass)}>
        <h2 className="min-w-0 flex-1 truncate text-[20px] leading-tight font-semibold tracking-[-0.012em] text-ink">
          {title}
        </h2>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
    </header>
  )
}
