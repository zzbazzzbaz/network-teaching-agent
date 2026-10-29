import { useEffect, useRef, useState } from "react"

import { BlockFallback } from "./block-fallback"

/** iframe 不继承页面样式，这里注入与全站一致的基础排版。 */
const BASE_STYLE = `
html, body { margin: 0; padding: 0; background: transparent; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: #c3cfcc; border-radius: 4px; }
::-webkit-scrollbar-track { background: transparent; }
body {
  color: #121a1c;
  padding: 12px;
  font-family: "IBM Plex Sans", "PingFang SC", "Hiragino Sans GB",
    "Noto Sans CJK SC", "Microsoft YaHei", ui-sans-serif, system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.7;
}
`

const DEBOUNCE_MS = 350
const INITIAL_HEIGHT = 320
const MIN_HEIGHT = 120
const MAX_HEIGHT = 900

function buildSrcDoc(html: string): string {
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>${BASE_STYLE}</style></head><body>${html}</body></html>`
}

export function HtmlBlock({ code }: { code: string }) {
  const [rendered, setRendered] = useState<string | null>(null)
  const [height, setHeight] = useState(INITIAL_HEIGHT)
  const frameRef = useRef<HTMLIFrameElement | null>(null)
  const observerRef = useRef<ResizeObserver | null>(null)

  useEffect(() => {
    // 等代码块闭合：流式过程中每个 token 都会重渲染，直接更新 srcdoc 会让 iframe 反复重载。
    const timer = window.setTimeout(() => {
      setRendered((prev) => (prev === code ? prev : code))
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [code])

  useEffect(() => () => observerRef.current?.disconnect(), [])

  const handleLoad = () => {
    observerRef.current?.disconnect()
    const body = frameRef.current?.contentDocument?.body
    if (!body) return
    const measure = () => {
      const next = Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, body.scrollHeight))
      setHeight((prev) => (prev === next ? prev : next))
    }
    measure()
    const observer = new ResizeObserver(() => {
      // 在下一帧读取，避免 ResizeObserver 回调里改布局触发 loop 警告。
      window.requestAnimationFrame(measure)
    })
    observer.observe(body)
    observerRef.current = observer
  }

  if (!code.trim()) {
    return <div className="text-[11px] text-ink-muted">图表生成中…</div>
  }

  if (!code.includes("<")) {
    return <BlockFallback code={code} reason="这不是一段 HTML，已显示源码。" />
  }

  if (rendered === null) {
    return <div className="text-[11px] text-ink-muted">图表生成中…</div>
  }

  return (
    <div className="html-block">
      <iframe
        ref={frameRef}
        title="配图"
        srcDoc={buildSrcDoc(rendered)}
        loading="lazy"
        style={{ height }}
        onLoad={handleLoad}
      />
    </div>
  )
}
