import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 rounded-sm border px-1.5 py-0.5 text-[11px] leading-4 font-medium whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "border-transparent bg-link-soft text-link-strong",
        outline: "border-line bg-surface text-ink-muted",
        muted: "border-transparent bg-surface-3 text-ink-muted",
        signal: "border-signal-line bg-signal-soft text-signal",
        danger: "border-danger-line bg-danger-soft text-danger",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
