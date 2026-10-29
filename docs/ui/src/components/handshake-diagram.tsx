export function HandshakeDiagram({
  className = "",
  tone = "light",
}: {
  className?: string
  tone?: "light" | "dark"
}) {
  const dark = tone === "dark"
  const line = dark ? "rgba(255,255,255,0.18)" : "var(--line-strong)"
  const strong = dark ? "rgba(255,255,255,0.36)" : "var(--line-strong)"
  const label = dark ? "rgba(255,255,255,0.56)" : "var(--ink-muted)"
  const link = dark ? "#7fd8cb" : "var(--link)"
  const signal = dark ? "#e7b36a" : "var(--signal)"
  const surface = dark ? "#121a1c" : "var(--surface)"

  return (
    <div className={className}>
      <svg
        viewBox="0 0 400 160"
        role="img"
        aria-label="TCP 三次握手：客户端发送 SYN，服务器回复 SYN 和 ACK，客户端再发送 ACK"
        className="h-auto w-full"
      >
        <defs>
          <marker
            id="handshake-arrow-link"
            viewBox="0 0 6 6"
            refX="5.5"
            refY="3"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0 0 L6 3 L0 6 Z" fill={link} />
          </marker>
          <marker
            id="handshake-arrow-signal"
            viewBox="0 0 6 6"
            refX="5.5"
            refY="3"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0 0 L6 3 L0 6 Z" fill={signal} />
          </marker>
        </defs>

        <g fontFamily="IBM Plex Mono, monospace">
          <text x="84" y="12" textAnchor="middle" fontSize="9.5" fill={label}>
            客户端
          </text>
          <text x="316" y="12" textAnchor="middle" fontSize="9.5" fill={label}>
            服务器
          </text>
        </g>

        <g stroke={line} strokeWidth="1" strokeDasharray="3 4">
          <line x1="84" y1="26" x2="84" y2="146" />
          <line x1="316" y1="26" x2="316" y2="146" />
        </g>

        <g fill={surface} stroke={strong} strokeWidth="1">
          <circle cx="84" cy="26" r="2.4" />
          <circle cx="316" cy="26" r="2.4" />
        </g>

        <line
          x1="84"
          y1="52"
          x2="316"
          y2="52"
          stroke={signal}
          strokeWidth="1.2"
          markerEnd="url(#handshake-arrow-signal)"
        />
        <circle cx="84" cy="52" r="3" fill={signal} />
        <text
          x="200"
          y="43"
          textAnchor="middle"
          fontFamily="IBM Plex Mono, monospace"
          fontSize="10"
          fill={signal}
        >
          SYN
        </text>
        <text
          x="200"
          y="65"
          textAnchor="middle"
          fontFamily="IBM Plex Mono, monospace"
          fontSize="8.5"
          fill={label}
        >
          seq = x
        </text>

        <line
          x1="316"
          y1="88"
          x2="84"
          y2="88"
          stroke={link}
          strokeWidth="1.2"
          markerEnd="url(#handshake-arrow-link)"
        />
        <text
          x="200"
          y="79"
          textAnchor="middle"
          fontFamily="IBM Plex Mono, monospace"
          fontSize="10"
          fill={link}
        >
          SYN + ACK
        </text>
        <text
          x="200"
          y="101"
          textAnchor="middle"
          fontFamily="IBM Plex Mono, monospace"
          fontSize="8.5"
          fill={label}
        >
          seq = y · ack = x + 1
        </text>

        <line
          x1="84"
          y1="124"
          x2="316"
          y2="124"
          stroke={link}
          strokeWidth="1.2"
          markerEnd="url(#handshake-arrow-link)"
        />
        <text
          x="200"
          y="115"
          textAnchor="middle"
          fontFamily="IBM Plex Mono, monospace"
          fontSize="10"
          fill={link}
        >
          ACK
        </text>
        <text
          x="200"
          y="137"
          textAnchor="middle"
          fontFamily="IBM Plex Mono, monospace"
          fontSize="8.5"
          fill={label}
        >
          ack = y + 1
        </text>
      </svg>
    </div>
  )
}
