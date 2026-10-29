const LAYERS = [
  { label: "应用层", y: 28 },
  { label: "传输层", y: 66 },
  { label: "网络层", y: 104 },
  { label: "数据链路层", y: 142 },
  { label: "物理层", y: 180 },
]

export function LayerDiagram({
  className = "",
  tone = "light",
}: {
  className?: string
  tone?: "light" | "dark"
}) {
  const dark = tone === "dark"
  const line = dark ? "rgba(255,255,255,0.18)" : "var(--line-strong)"
  const strong = dark ? "rgba(255,255,255,0.36)" : "var(--line-strong)"
  const label = dark ? "rgba(255,255,255,0.58)" : "var(--ink-muted)"
  const signal = dark ? "#e7b36a" : "var(--signal)"
  const signalSoft = dark
    ? "rgba(231,179,106,0.16)"
    : "var(--signal-soft)"
  const surface = dark ? "#121a1c" : "var(--surface)"

  return (
    <div className={className}>
      <svg
        viewBox="0 0 400 208"
        role="img"
        aria-label="一次请求依次穿过应用层、传输层、网络层、数据链路层和物理层"
        className="h-auto w-full"
      >
        <g fontFamily="IBM Plex Mono, monospace" fontSize="10" fill={label}>
          {LAYERS.map((layer) => (
            <text key={layer.label} x="0" y={layer.y + 3.5}>
              {layer.label}
            </text>
          ))}
        </g>

        <g stroke={line} strokeWidth="1">
          {LAYERS.map((layer) => (
            <line key={layer.label} x1="72" y1={layer.y} x2="400" y2={layer.y} />
          ))}
        </g>

        <line
          x1="296"
          y1="14"
          x2="296"
          y2="194"
          stroke={dark ? "rgba(127,216,203,0.45)" : "var(--link-line)"}
          strokeWidth="1"
          strokeDasharray="3 4"
        />

        {LAYERS.map((layer) => (
          <circle
            key={layer.label}
            cx="296"
            cy={layer.y}
            r="2.6"
            fill={surface}
            stroke={strong}
            strokeWidth="1.2"
          />
        ))}

        <circle cx="296" cy="66" r="6.5" fill={signalSoft} />
        <circle cx="296" cy="66" r="3.2" fill={signal} />

        <g fontFamily="IBM Plex Mono, monospace" fontSize="9" fill={signal}>
          <text x="308" y="59">SYN · seq=x</text>
        </g>

        <g stroke={line} strokeWidth="1" strokeDasharray="2 4">
          <line x1="72" y1="194" x2="400" y2="194" />
        </g>
        <text
          x="72"
          y="206"
          fontFamily="IBM Plex Mono, monospace"
          fontSize="9"
          fill={label}
        >
          一次请求的路径
        </text>
      </svg>
    </div>
  )
}
