import { Menu, ArrowLeft } from "lucide-react"

import { Button } from "@/shared/ui/button"
import { cn } from "@/shared/lib/utils"

import { useShell } from "./context"

export function WorkspaceBar({
  title,
  onBack,
  className,
}: {
  title: string
  onBack?: () => void
  className?: string
}) {
  const { openNav } = useShell()

  return (
    <header
      className={cn(
        "flex h-[52px] shrink-0 items-center gap-1.5 border-b border-line bg-surface px-2.5 lg:hidden",
        className,
      )}
    >
      <Button
        variant="ghost"
        size="icon"
        className="size-11 shrink-0"
        aria-label="打开会话列表"
        onClick={openNav}
      >
        <Menu className="size-4.5" aria-hidden="true" />
      </Button>

      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-semibold text-ink">{title}</p>
      </div>

      {onBack && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="size-11 shrink-0"
          aria-label="返回对话"
          title="返回对话"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
        </Button>
      )}
    </header>
  )
}
