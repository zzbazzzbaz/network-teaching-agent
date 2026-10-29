import { ArrowUp, ImagePlus, Square } from "lucide-react"
import {
  AuiIf,
  ComposerPrimitive,
} from "@assistant-ui/react"

import { ComposerImagePreview } from "@/features/files/ui/ComposerImagePreview"
import { Button } from "@/shared/ui/button"
import { cn } from "@/shared/lib/utils"

export function Composer({
  mode,
  empty,
}: {
  mode: "learn" | "lab"
  empty: boolean
}) {
  const placeholder =
    mode === "learn"
      ? empty
        ? "先说说你看到的、你猜的…"
        : "继续追问，或说说你的想法…"
      : empty
        ? "说说你想验证什么…"
        : "描述你想验证的步骤…"

  return (
    <div className="shrink-0 bg-surface px-4 pt-2 pb-[max(16px,env(safe-area-inset-bottom))] lg:px-8">
      <ComposerPrimitive.Root
        className={cn(
          "mx-auto w-full max-w-[1000px] rounded-lg border border-line-strong bg-surface transition-[border-color,box-shadow] focus-within:border-link focus-within:ring-2 focus-within:ring-ring/10",
        )}
      >
        <AuiIf condition={(state) => state.composer.attachments.length > 0}>
          <div className="flex flex-wrap gap-2 px-3 pt-2">
            <ComposerPrimitive.Attachments>
              {({ attachment }) => (
                <ComposerImagePreview attachment={attachment} />
              )}
            </ComposerPrimitive.Attachments>
          </div>
        </AuiIf>
        <label htmlFor="composer" className="sr-only">
          给老师发消息
        </label>
        <ComposerPrimitive.Input
          id="composer"
          name="message"
          rows={1}
          submitMode="enter"
          placeholder={placeholder}
          className="block max-h-40 min-h-11 w-full resize-none bg-transparent px-3.5 pt-3 pb-1 text-[16px] leading-6 text-ink outline-none placeholder:text-ink-muted/70 lg:text-[14px]"
        />

        <div className="flex items-center justify-between gap-1 px-2.5 pb-2">
          <div className="flex items-center">
            <AuiIf condition={(state) => state.composer.attachments.length < 3}>
              <ComposerPrimitive.AddAttachment multiple asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="添加图片"
                  title="添加图片"
                >
                  <ImagePlus className="size-4" aria-hidden="true" />
                </Button>
              </ComposerPrimitive.AddAttachment>
            </AuiIf>
          </div>
          <div className="flex items-center gap-1">
            <AuiIf condition={(state) => state.thread.isRunning}>
              <ComposerPrimitive.Cancel asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1.5 text-[11.5px]"
                >
                  <Square className="size-2.5 fill-current" aria-hidden="true" />
                  停止
                </Button>
              </ComposerPrimitive.Cancel>
            </AuiIf>
            <ComposerPrimitive.Send asChild>
              <Button
                type="submit"
                size="icon"
                aria-label="发送消息"
                className="size-10 rounded-md sm:size-8"
              >
                <ArrowUp className="size-4" aria-hidden="true" />
              </Button>
            </ComposerPrimitive.Send>
          </div>
        </div>
      </ComposerPrimitive.Root>
    </div>
  )
}
