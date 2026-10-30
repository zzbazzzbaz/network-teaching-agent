import { Check } from "lucide-react"
import { useMemo } from "react"

import { cn } from "@/shared/lib/utils"

import { pretty } from "../../model/tool-call"

export function ImportQuestionsResult({
  result,
  isError,
}: {
  result: unknown
  isError?: boolean
}) {
  const resultText = useMemo(() => pretty(result), [result])

  return (
    <div className="flex items-start gap-2 rounded-md border border-line bg-surface-2/60 px-3 py-2 text-[11.5px] leading-5">
      <Check
        className={cn(
          "mt-0.5 size-3.5 shrink-0",
          isError ? "text-danger" : "text-link",
        )}
        aria-hidden="true"
      />
      <span className="shrink-0 text-ink-soft">导入题目</span>
      <span className="min-w-0 flex-1 truncate text-ink-muted">
        {resultText || (isError ? "失败" : "完成")}
      </span>
    </div>
  )
}
