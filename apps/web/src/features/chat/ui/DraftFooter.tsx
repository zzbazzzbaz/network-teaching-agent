import { ThreadPrimitive } from "@assistant-ui/react"

import type { Mode } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"
import { workspaceContentClass } from "@/shared/ui/workspace-header"

import { STARTERS } from "../model/starters"
import { Composer } from "./Composer"

const PLACEHOLDERS: Record<Mode, string> = {
  learn: "直接问老师，或从上面的章节开始…",
  lab: "说说你想观察或验证什么…",
}

export function DraftFooter({
  mode,
  starting,
  onStarter,
}: {
  mode: Mode
  starting: boolean
  onStarter: (text: string) => void
}) {
  return (
    <footer className="shrink-0 border-t border-line bg-surface">
      {starting ? (
        <p
          className={cn(
            workspaceContentClass,
            "pt-2.5 text-[11.5px] text-ink-muted",
          )}
          role="status"
        >
          正在开始对话…
        </p>
      ) : (
        <div
          className={cn(
            workspaceContentClass,
            "flex flex-wrap gap-1.5 pt-2.5 pb-0.5",
          )}
        >
          {STARTERS[mode].map((starter) => (
            <button
              key={starter}
              type="button"
              onClick={() => onStarter(starter)}
              className="rounded-full border border-line px-2.5 py-1 text-[11.5px] text-ink-muted transition-colors hover:border-link-line hover:text-ink"
            >
              {starter}
            </button>
          ))}
        </div>
      )}

      <ThreadPrimitive.Root>
        <Composer mode={mode} empty placeholder={PLACEHOLDERS[mode]} />
      </ThreadPrimitive.Root>
    </footer>
  )
}
