import { useEffect, useId, useMemo, useState } from "react";
import DOMPurify from "dompurify";
import type { MermaidConfig } from "mermaid";

import type { SyntaxHighlighterProps } from "@assistant-ui/react-markdown";

type MermaidTheme = NonNullable<MermaidConfig["theme"]>;

type MermaidApi = typeof import("mermaid").default;

let mermaidPromise: Promise<MermaidApi> | undefined;
let initializedTheme: MermaidTheme | undefined;

async function loadMermaid(theme: MermaidTheme): Promise<MermaidApi> {
  mermaidPromise ??= import("mermaid").then((module) => module.default);
  const mermaid = await mermaidPromise;

  if (initializedTheme !== theme) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme,
      htmlLabels: false,
    });
    initializedTheme = theme;
  }

  return mermaid;
}

function prefersDarkMode(): boolean {
  const root = document.documentElement;
  const explicitTheme = root.dataset.theme;
  if (explicitTheme === "dark") return true;
  if (explicitTheme === "light") return false;
  if (root.classList.contains("dark")) return true;

  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function useMermaidTheme(): MermaidTheme {
  const [isDark, setIsDark] = useState(prefersDarkMode);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setIsDark(prefersDarkMode());

    media.addEventListener("change", update);
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "data-theme"],
    });

    return () => {
      media.removeEventListener("change", update);
      observer.disconnect();
    };
  }, []);

  return isDark ? "dark" : "default";
}

function sanitizeSvg(svg: string): string {
  return DOMPurify.sanitize(svg, {
    USE_PROFILES: { svg: true, svgFilters: true },
    FORBID_TAGS: ["script", "foreignObject"],
  });
}

function cleanupMermaidTempNodes(renderId: string): void {
  document.getElementById(`d${renderId}`)?.remove();
  document.getElementById(`i${renderId}`)?.remove();
}

function MermaidFallback({ code }: { code: string }) {
  return (
    <div className="mermaid-fallback" data-testid="mermaid-fallback">
      <div className="mermaid-error" role="status">
        图表渲染失败，已显示源码。
      </div>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  );
}

function MermaidRender({
  code,
  theme,
  className,
}: {
  code: string;
  theme: MermaidTheme;
  className?: string;
}) {
  const reactId = useId();
  const renderId = useMemo(
    () => `mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`,
    [reactId],
  );
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const mermaid = await loadMermaid(theme);
        const result = await mermaid.render(renderId, code);
        if (!cancelled) {
          setSvg(sanitizeSvg(result.svg));
        }
      } catch {
        if (!cancelled) {
          setFailed(true);
        }
      } finally {
        cleanupMermaidTempNodes(renderId);
      }
    })();

    return () => {
      cancelled = true;
      cleanupMermaidTempNodes(renderId);
    };
  }, [code, renderId, theme]);

  if (failed) return <MermaidFallback code={code} />;

  if (svg === null) {
    return (
      <div className="mermaid-loading" data-testid="mermaid-loading">
        图表渲染中…
      </div>
    );
  }

  return (
    <div
      className={`mermaid-diagram${className ? ` ${className}` : ""}`}
      data-testid="mermaid-diagram"
      data-mermaid-theme={theme}
      role="img"
      aria-label="Mermaid 图表"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

type MermaidDiagramProps = Pick<SyntaxHighlighterProps, "code"> & {
  language?: string;
  className?: string;
};

export function MermaidDiagram({ code, className }: MermaidDiagramProps) {
  const theme = useMermaidTheme();

  if (!code.trim()) {
    return <MermaidFallback code={code} />;
  }

  return (
    <MermaidRender
      key={`${theme}:${code}`}
      code={code}
      theme={theme}
      className={className}
    />
  );
}
