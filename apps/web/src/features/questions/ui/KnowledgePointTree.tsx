import { Check, ChevronRight } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import type { KnowledgePoint } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"

import {
  buildKnowledgePointTree,
  knowledgePointAncestors,
  type KnowledgePointTreeNode,
} from "../model"

const INDENT = 14

interface KnowledgePointTreeProps {
  nodes: KnowledgePoint[]
  value?: string
  onSelect: (id: string) => void
  className?: string
}

/**
 * 教材目录树：一级是章，展开后是节和子节。
 * 行点击选中该知识点，箭头单独负责展开/收起，两者互不影响。
 */
export function KnowledgePointTree({
  nodes,
  value,
  onSelect,
  className,
}: KnowledgePointTreeProps) {
  const tree = useMemo(() => buildKnowledgePointTree(nodes), [nodes])
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(knowledgePointAncestors(nodes, value)),
  )

  // 外部选中变化（例如筛选被重置）时，把选中项所在分支展开。
  useEffect(() => {
    setExpanded((previous) => {
      const next = new Set(previous)
      for (const id of knowledgePointAncestors(nodes, value)) next.add(id)
      return next.size === previous.size &&
        [...next].every((id) => previous.has(id))
        ? previous
        : next
    })
  }, [nodes, value])

  function toggle(id: string) {
    setExpanded((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <ul role="tree" aria-label="知识点目录" className={cn("space-y-px", className)}>
      {tree.map((node) => (
        <TreeRow
          key={node.id}
          node={node}
          depth={0}
          value={value}
          expanded={expanded}
          onToggle={toggle}
          onSelect={onSelect}
        />
      ))}
    </ul>
  )
}

function TreeRow({
  node,
  depth,
  value,
  expanded,
  onToggle,
  onSelect,
}: {
  node: KnowledgePointTreeNode
  depth: number
  value?: string
  expanded: Set<string>
  onToggle: (id: string) => void
  onSelect: (id: string) => void
}) {
  const hasChildren = node.children.length > 0
  const open = expanded.has(node.id)
  const selected = node.id === value

  return (
    <li
      role="treeitem"
      aria-selected={selected}
      aria-expanded={hasChildren ? open : undefined}
    >
      <div
        className="flex items-center"
        style={{ paddingLeft: depth * INDENT }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => onToggle(node.id)}
            aria-label={`${open ? "收起" : "展开"} ${node.id} ${node.title}`}
            className="flex size-6 shrink-0 items-center justify-center rounded-sm text-ink-muted transition-colors hover:bg-surface-3 hover:text-ink"
          >
            <ChevronRight
              className={cn("size-3.5 transition-transform", open && "rotate-90")}
              aria-hidden="true"
            />
          </button>
        ) : (
          <span className="size-6 shrink-0" aria-hidden="true" />
        )}

        <button
          type="button"
          onClick={() => onSelect(node.id)}
          aria-current={selected ? "true" : undefined}
          className={cn(
            "flex min-w-0 flex-1 items-center gap-2 rounded-sm px-1.5 py-1 text-left transition-colors",
            selected
              ? "bg-surface-3 text-ink"
              : "text-ink-soft hover:bg-surface-2 hover:text-ink",
          )}
        >
          <span
            className={cn(
              "w-11 shrink-0 font-mono text-[10.5px] tabular-nums",
              selected ? "text-link" : "text-ink-muted",
            )}
          >
            {node.id}
          </span>
          <span className="truncate text-[12px]">{node.title}</span>
          {selected && (
            <Check className="ml-auto size-3.5 shrink-0 text-link" aria-hidden="true" />
          )}
        </button>
      </div>

      {hasChildren && open && (
        <ul role="group" className="space-y-px">
          {node.children.map((child) => (
            <TreeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              value={value}
              expanded={expanded}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
