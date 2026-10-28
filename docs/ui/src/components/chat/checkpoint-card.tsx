import { CheckCircle2 } from "lucide-react"
import { useId, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { Checkpoint, Session } from "@/lib/mock"
import { useStore } from "@/lib/store"
import { cn, formatTime } from "@/lib/utils"

export function CheckpointCard({
  session,
  messageId,
  partId,
  checkpoint,
}: {
  session: Session
  messageId: string
  partId: string
  checkpoint: Checkpoint
}) {
  const { submitCheckpoint } = useStore()
  const uid = useId()
  const [selected, setSelected] = useState("")

  const submittedOption = checkpoint.submitted
    ? checkpoint.options.find((option) => option.startsWith(checkpoint.submitted!))
    : undefined

  if (checkpoint.submitted) {
    return (
      <div className="w-full max-w-[640px] overflow-hidden rounded-lg border border-line bg-surface-2/70">
        <div className="flex items-center gap-2 px-4 py-2.5">
          <CheckCircle2 className="size-3.5 text-link" aria-hidden="true" />
          <span className="text-[11px] text-ink-muted">
            已作答
            {checkpoint.submittedAt && ` · ${formatTime(checkpoint.submittedAt)}`}
          </span>
          <Badge
            variant={checkpoint.correct ? "default" : "signal"}
            className="ml-auto"
          >
            {checkpoint.correct ? "回答正确" : "再想一步"}
          </Badge>
        </div>
        <div className="border-t border-line/70 px-4 py-2.5">
          <p className="line-clamp-2 text-[12.5px] leading-5 text-ink-soft">
            {checkpoint.prompt}
          </p>
          <p className="mt-1.5 text-[11.5px] text-ink-muted">
            你的选择：{submittedOption}
          </p>
        </div>
      </div>
    )
  }

  return (
    <fieldset className="w-full max-w-[640px] overflow-hidden rounded-lg border border-signal-line bg-signal-soft/35 text-left">
      <legend className="sr-only">{checkpoint.prompt}</legend>

      <div className="flex items-center gap-2 border-b border-signal-line/60 px-4 py-2">
        <span className="size-1.5 rounded-full bg-signal" aria-hidden="true" />
        <span className="text-[11px] font-medium text-signal">作答检查点</span>
        <span className="ml-auto font-mono text-[10px] text-signal/60">
          ask_student
        </span>
      </div>

      <div className="px-4 pt-3.5 pb-1">
        <p className="text-[14px] leading-6 font-medium text-ink">
          {checkpoint.prompt}
        </p>
      </div>

      <RadioGroup
        value={selected}
        onValueChange={setSelected}
        aria-label={checkpoint.prompt}
        className="mt-2 gap-0 border-t border-signal-line/40"
      >
        {checkpoint.options.map((option, index) => {
          const letter = option.charAt(0)
          const id = `${uid}-${index}`
          return (
            <label
              key={option}
              htmlFor={id}
              className={cn(
                "flex cursor-pointer items-start gap-3 border-b border-signal-line/40 px-4 py-3 transition-colors last:border-b-0",
                "hover:bg-signal-soft/50 has-[[data-state=checked]]:bg-signal-soft/60",
              )}
            >
              <RadioGroupItem
                id={id}
                value={letter}
                className="mt-0.5 border-signal/45 data-[state=checked]:border-signal data-[state=checked]:bg-signal"
              />
              <span className="text-[13px] leading-5 text-ink">{option}</span>
            </label>
          )
        })}
      </RadioGroup>

      <div className="flex items-center gap-3 border-t border-signal-line/50 px-4 py-3">
        <span className="min-w-0 flex-1 text-[11px] leading-4 text-ink-muted">
          提交后对话继续，也可以补充理由。
        </span>
        <Button
          type="button"
          disabled={!selected}
          onClick={() =>
            submitCheckpoint(
              session,
              messageId,
              partId,
              checkpoint.questionId,
              selected,
            )
          }
          className="h-11 shrink-0 bg-signal px-4 text-white hover:bg-[#7d4700] focus-visible:ring-signal/30 sm:h-10"
        >
          提交作答
        </Button>
      </div>
    </fieldset>
  )
}
