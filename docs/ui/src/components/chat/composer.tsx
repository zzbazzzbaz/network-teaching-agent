import { ArrowUp, Square } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import type { Mode } from "@/lib/mock"
import { cn } from "@/lib/utils"

export function Composer({
  mode,
  busy,
  checkpointOpen,
  empty,
  onSend,
  onStop,
}: {
  mode: Mode
  busy: boolean
  checkpointOpen: boolean
  empty: boolean
  onSend: (text: string) => void
  onStop: () => void
}) {
  const [value, setValue] = useState("")
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    element.style.height = "0px"
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`
  }, [value])

  function submit() {
    const text = value.trim()
    if (!text || busy) return
    onSend(text)
    setValue("")
    requestAnimationFrame(() => ref.current?.focus())
  }

  return (
    <div className="shrink-0 bg-surface px-4 pt-2 pb-[max(16px,env(safe-area-inset-bottom))] lg:px-8">
      <form
        className="mx-auto w-full max-w-[840px]"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <div className="rounded-lg border border-line-strong bg-surface transition-[border-color,box-shadow] focus-within:border-link focus-within:ring-2 focus-within:ring-ring/10">
          <label htmlFor="composer" className="sr-only">
            给老师发消息
          </label>
          <textarea
            id="composer"
            name="message"
            ref={ref}
            rows={1}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              const composing =
                event.nativeEvent.isComposing ||
                (event.nativeEvent as KeyboardEvent).keyCode === 229
              if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !composing
              ) {
                event.preventDefault()
                submit()
              }
            }}
            placeholder={
              checkpointOpen
                ? "也可以直接说说你的思路…"
                : empty
                  ? mode === "learn"
                    ? "先说说你看到的、你猜的…"
                    : "说说你想验证什么…"
                  : mode === "learn"
                    ? "继续追问，或说说你的想法…"
                    : "描述你想验证的步骤…"
            }
            className="block max-h-40 min-h-11 w-full resize-none bg-transparent px-3.5 pt-3 pb-1 text-[16px] leading-6 text-ink outline-none placeholder:text-ink-muted/70 lg:text-[14px]"
          />

          <div className="flex items-center justify-end gap-1 px-2.5 pb-2">
            {busy && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onStop}
                className="h-8 gap-1.5 text-[11.5px]"
              >
                <Square className="size-2.5 fill-current" aria-hidden="true" />
                停止
              </Button>
            )}
            <Button
              type="submit"
              size="icon"
              aria-label="发送消息"
              disabled={!value.trim() || busy}
              className={cn("size-10 rounded-md sm:size-8")}
            >
              <ArrowUp className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </form>
    </div>
  )
}
