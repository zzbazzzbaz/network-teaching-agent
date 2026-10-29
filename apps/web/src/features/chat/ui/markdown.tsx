import { useEffect, useId, useRef, useState, isValidElement, type ReactNode } from "react"
import DOMPurify from "dompurify"
import type { MermaidConfig } from "mermaid"
import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown"
import type { SyntaxHighlighterProps } from "@assistant-ui/react-markdown"

import { cn } from "@/shared/lib/utils"

import { BlockFallback } from "./block-fallback"
import { EChartsBlock } from "./echarts-block"
import { HtmlBlock } from "./html-block"

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
  const renderSequence = useRef(0)
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const baseId = `mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`
    // StrictMode 会重复执行 effect；每次渲染使用独立临时 ID，避免同一节点被并发清理。
    const renderId = `${baseId}-${renderSequence.current++}`
    let cancelled = false
    void (async () => {
      try {
        const mermaid = await loadMermaid(theme)
        const result = await mermaid.render(renderId, code)
        if (!cancelled) setSvg(sanitizeSvg(result.svg))
      } catch (error) {
        if (cancelled) return
        console.error("Mermaid 渲染失败", error)
        setFailed(true)
      } finally {
        cleanupMermaidTempNodes(renderId)
      }
    })()

    return () => {
      cancelled = true
      cleanupMermaidTempNodes(renderId)
    }
  }, [code, reactId, theme])

  if (failed) return <BlockFallback code={code} />
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
  if (!code.trim()) return <BlockFallback code={code} />
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

const blockRenderers = new Map<string, (code: string) => ReactNode>([
  ["mermaid", (code) => <MermaidDiagram code={code} />],
  ["html", (code) => <HtmlBlock code={code} />],
  ["echarts", (code) => <EChartsBlock code={code} />],
])

const blockComponents = {
  mermaid: { SyntaxHighlighter: MermaidDiagram },
  html: { SyntaxHighlighter: HtmlBlock },
  echarts: { SyntaxHighlighter: EChartsBlock },
}

function languageOf(className: string | undefined): string | undefined {
  return className
    ?.split(/\s+/)
    .find((name) => name.startsWith("language-"))
    ?.slice("language-".length)
}

/** 把 ```mermaid / ```html / ```echarts 代码块交给对应渲染器，其余 pre 原样返回。 */
function MarkdownPre({ children }: { children?: ReactNode }) {
  const only =
    Array.isArray(children) && children.length === 1 ? children[0] : children
  if (isValidElement(only)) {
    const { className, children: code } = only.props as {
      className?: string
      children?: ReactNode
    }
    const render = blockRenderers.get(languageOf(className) ?? "")
    if (render) return render(String(code ?? ""))
  }
  return <pre>{children}</pre>
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
      componentsByLanguage={blockComponents}
      urlTransform={safeUrlTransform}
      skipHtml
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
        skipHtml
        components={{
          ...commonComponents,
          pre: MarkdownPre,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}
