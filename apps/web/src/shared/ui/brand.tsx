import { Link } from "@tanstack/react-router"

import { cn } from "@/shared/lib/utils"

export function LayerMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={cn("size-5", className)}
      fill="none"
    >
      <g stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
        <path d="M3.5 6.5h17" opacity="0.35" />
        <path d="M3.5 12h17" opacity="0.6" />
        <path d="M3.5 17.5h17" />
      </g>
      <g fill="currentColor">
        <circle cx="8" cy="6.5" r="1.9" opacity="0.45" />
        <circle cx="14.5" cy="12" r="1.9" opacity="0.75" />
        <circle cx="19" cy="17.5" r="1.9" />
      </g>
    </svg>
  )
}

export function Wordmark({
  className,
  tone = "default",
  to = "/learn",
  onClick,
  compact = false,
}: {
  className?: string
  tone?: "default" | "dark"
  to?: string
  onClick?: () => void
  compact?: boolean
}) {
  const dark = tone === "dark"

  return (
    <Link
      to={to}
      onClick={onClick}
      aria-label="链路 · 返回工作台"
      className={cn(
        "group flex items-center rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/30",
        compact ? "justify-center" : "gap-2.5",
        className,
      )}
    >
      <span
        className={cn(
          "flex items-center justify-center rounded-md border transition-colors",
          compact ? "size-9" : "size-8",
          dark
            ? "border-white/15 bg-white/10 text-white group-hover:bg-white/15"
            : "border-line bg-surface-2 text-link group-hover:border-link-line group-hover:bg-link-soft",
        )}
      >
        <LayerMark />
      </span>
      {!compact && (
        <span
          className={cn(
            "block text-[15px] font-semibold leading-tight tracking-tight",
            dark ? "text-white" : "text-ink",
          )}
        >
          链路
        </span>
      )}
    </Link>
  )
}
