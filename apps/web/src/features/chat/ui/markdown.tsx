import { useEffect, useId, useMemo, useState } from "react"
import DOMPurify from "dompurify"
import type { MermaidConfig } from "mermaid"
import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown"
import type { SyntaxHighlighterProps } from "@assistant-ui/react-markdown"

import { cn } from "@/shared/lib/utils"

type MermaidTheme = NonNullable<MermaidConfig["theme"]>
type MermaidApi = typeof import("mermaid").default

let mermaidPromise: Promise<MermaidApi> | undefined
let initializedTheme: MermaidTheme | undefined

async function loadMermaid(theme: MermaidTheme): Promise<MermaidApi> {
  mermaidPromise ??= import("mermaid").then((module) => module.default)
  const mermaid = await mermaidPromise

  if (initializedTheme !== theme) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme,
      htmlLabels: false,
    })
    initializedTheme = theme
  }

  return mermaid
}

function sanitizeSvg(svg: string): string {
  return DOMPurify.sanitize(svg, {
    USE_PROFILES: { svg: true, svgFilters: true },
    FORBID_TAGS: ["script", "foreignObject"],
  })
}

function cleanupMermaidTempNodes(renderId: string): void {
  document.getElementById(`d${renderId}`)?.remove()
  document.getElementById(`i${renderId}`)?.remove()
}

function MermaidFallback({ code }: { code: string }) {
  return (
    <div className="rounded-md border border-line bg-surface-2 p-3">
      <div className="text-[11px] text-ink-muted">图表渲染失败，已显示源码。</div>
      <pre className="mt-2 overflow-x-auto text-[11px] leading-5">
        <code>{code}</code>
      </pre>
    </div>
  )
}

function MermaidRender({
  code,
  theme,
  className,
}: {
  code: string
  theme: MermaidTheme
  className?: string
}) {
  const reactId = useId()
  const renderId = useMemo(
    () => `mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`,
    [reactId],
  )
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const mermaid = await loadMermaid(theme)
        const result = await mermaid.render(renderId, code)
        if (!cancelled) setSvg(sanitizeSvg(result.svg))
      } catch {
        if (!cancelled) setFailed(true)
      } finally {
        cleanupMermaidTempNodes(renderId)
      }
    })()

    return () => {
      cancelled = true
      cleanupMermaidTempNodes(renderId)
    }
  }, [code, renderId, theme])

  if (failed) return <MermaidFallback code={code} />
  if (svg === null) {
    return <div className="text-[11px] text-ink-muted">图表渲染中…</div>
  }

  return (
    <div
      className={cn("mermaid-diagram overflow-x-auto", className)}
      role="img"
      aria-label="Mermaid 图表"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

export function MermaidDiagram({
  code,
  className,
}: Pick<SyntaxHighlighterProps, "code"> & { className?: string }) {
  if (!code.trim()) return <MermaidFallback code={code} />
  return (
    <MermaidRender key={`default:${code}`} code={code} theme="default" className={className} />
  )
}

export function safeUrlTransform(url: string): string {
  if (url.startsWith("//")) return ""
  if (url.startsWith("/") || url.startsWith("#") || url.startsWith("?")) {
    return url
  }
  try {
    const parsed = new URL(url, window.location.href)
    if (parsed.protocol === "http:" || parsed.protocol === "https:") return url
  } catch {
    return ""
  }
  return ""
}

const mermaidComponents = {
  mermaid: { SyntaxHighlighter: MermaidDiagram },
}

const commonComponents: Components = {
  h1: ({ children }) => <h2>{children}</h2>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="md-table-wrap scroll-slim" tabIndex={0}>
      <table>{children}</table>
    </div>
  ),
}

export function MarkdownText() {
  return (
    <MarkdownTextPrimitive
      className="prose-chat"
      remarkPlugins={[remarkGfm]}
      components={commonComponents}
      componentsByLanguage={mermaidComponents}
      urlTransform={safeUrlTransform}
      defer
    />
  )
}

export function StaticMarkdown({
  text,
  className,
  tone = "chat",
}: {
  text: string
  className?: string
  tone?: "chat" | "note"
}) {
  return (
    <div className={cn(tone === "chat" ? "prose-chat" : "prose-note", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={safeUrlTransform}
        components={{
          ...commonComponents,
          pre: ({ children }) => <pre>{children}</pre>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}
