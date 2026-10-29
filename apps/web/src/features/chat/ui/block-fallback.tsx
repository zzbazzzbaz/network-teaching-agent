export function BlockFallback({
  code,
  reason = "图表渲染失败，已显示源码。",
}: {
  code: string
  reason?: string
}) {
  return (
    <div className="rounded-md border border-line bg-surface-2 p-3">
      <div className="text-[11px] text-ink-muted">{reason}</div>
      <pre className="mt-2 overflow-x-auto text-[11px] leading-5">
        <code>{code}</code>
      </pre>
    </div>
  )
}
