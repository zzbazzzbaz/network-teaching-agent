import ReactMarkdown, { type Components } from "react-markdown";
import type { Element } from "hast";
import remarkGfm from "remark-gfm";

import { MermaidDiagram } from "./MermaidDiagram";

function mermaidFromPre(node: Element | undefined): string | undefined {
  const child = node?.children[0];
  if (child?.type !== "element" || child.tagName !== "code") return undefined;

  const className = child.properties.className;
  const classes = Array.isArray(className)
    ? className.map(String)
    : [String(className ?? "")];
  const isMermaid = classes.some((name) =>
    name.split(/\s+/).includes("language-mermaid"),
  );
  if (!isMermaid) return undefined;

  return child.children
    .map((item) => (item.type === "text" ? item.value : ""))
    .join("");
}

export function safeUrlTransform(url: string): string {
  if (url.startsWith("//")) return "";
  if (url.startsWith("/") || url.startsWith("#") || url.startsWith("?")) {
    return url;
  }

  try {
    const parsed = new URL(url, window.location.href);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return url;
    }
  } catch {
    return "";
  }

  return "";
}

const components: Components = {
  pre({ node, children, ...props }) {
    const mermaid = mermaidFromPre(node);
    if (mermaid !== undefined) {
      return <MermaidDiagram code={mermaid} language="mermaid" />;
    }

    return <pre {...props}>{children}</pre>;
  },
};

export function MarkdownContent({
  content,
  className,
  testId,
}: {
  content: string;
  className?: string;
  testId?: string;
}) {
  return (
    <div className={`markdown${className ? ` ${className}` : ""}`} data-testid={testId}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        urlTransform={safeUrlTransform}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
