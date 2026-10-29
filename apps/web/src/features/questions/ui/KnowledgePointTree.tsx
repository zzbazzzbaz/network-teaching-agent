import { Check, ChevronRight } from "lucide-react"
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject,
} from "react"

import type { KnowledgePoint } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"

import {
  buildKnowledgePointTree,
  filterKnowledgePointTree,
  knowledgePointAncestors,
  type KnowledgePointTreeNode,
} from "../model"

const INDENT = 14

interface KnowledgePointTreeProps {
  nodes: KnowledgePoint[]
  value?: string
  onSelect: (id: string) => void
  counts?: Record<string, number>
  showEmpty?: boolean
  defaultExpandLevel?: number
  className?: string
}

type FlatRow = {
  node: KnowledgePointTreeNode
  depth: number
  parentId: string | null
  hasChildren: boolean
}

/**
 * 教材目录树：一级是章，展开后是节和子节。
 * 行点击选中该知识点，箭头单独负责展开/收起，两者互不影响。
 * counts 存在时在行尾显示子树题量；showEmpty=false 时隐藏 0 题分支。
 */
export function KnowledgePointTree({
  nodes,
  value,
  onSelect,
  counts,
  showEmpty = true,
  defaultExpandLevel = 0,
  className,
}: KnowledgePointTreeProps) {
  const tree = useMemo(() => buildKnowledgePointTree(nodes), [nodes])
  const filteredTree = useMemo(
    () =>
      counts
        ? filterKnowledgePointTree(tree, counts, {
            showEmpty,
            keepId: value,
          })
        : tree,
    [counts, showEmpty, tree, value],
  )
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [focusedId, setFocusedId] = useState<string | undefined>(value)
  const initializedRef = useRef(false)
  const selectedRef = useRef<HTMLButtonElement | null>(null)
  const rowRefs = useRef(new Map<string, HTMLButtonElement>())

  useEffect(() => {
    if (nodes.length === 0) return
    if (!initializedRef.current) {
      initializedRef.current = true
      const defaults = nodes
        .filter((node) => node.level <= defaultExpandLevel)
        .map((node) => node.id)
      if (defaults.length > 0) {
        setExpanded((previous) => new Set([...previous, ...defaults]))
      }
    }

    const ancestors = knowledgePointAncestors(nodes, value)
    if (ancestors.length === 0) return
    setExpanded((previous) => {
      const next = new Set(previous)
      for (const id of ancestors) next.add(id)
      return next.size === previous.size &&
        [...next].every((id) => previous.has(id))
        ? previous
        : next
    })
  }, [defaultExpandLevel, nodes, value])

  useEffect(() => {
    if (value) setFocusedId(value)
  }, [value])

  useEffect(() => {
    if (!value) return
    selectedRef.current?.scrollIntoView({ block: "nearest" })
  }, [filteredTree, value])

  const flatRows = useMemo(
    () => flattenRows(filteredTree, expanded),
    [expanded, filteredTree],
  )
  const focusableId =
    (focusedId && flatRows.some((row) => row.node.id === focusedId)
      ? focusedId
      : undefined) ??
    (value && flatRows.some((row) => row.node.id === value)
      ? value
      : flatRows[0]?.node.id)

  function toggle(id: string) {
    setExpanded((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function focusRow(id: string) {
    setFocusedId(id)
    requestAnimationFrame(() => rowRefs.current.get(id)?.focus())
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    row: FlatRow,
  ) {
    const index = flatRows.findIndex(
      (item) => item.node.id === row.node.id,
    )
    if (index < 0) return

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault()
      const nextIndex =
        event.key === "ArrowDown" ? index + 1 : index - 1
      const next = flatRows[nextIndex]
      if (next) focusRow(next.node.id)
      return
    }

    if (event.key === "Home" || event.key === "End") {
      event.preventDefault()
      const next =
        event.key === "Home" ? flatRows[0] : flatRows.at(-1)
      if (next) focusRow(next.node.id)
      return
    }

    if (event.key === "ArrowRight") {
      if (!row.hasChildren) return
      event.preventDefault()
      if (!expanded.has(row.node.id)) {
        toggle(row.node.id)
        return
      }
      const next = flatRows[index + 1]
      if (next?.parentId === row.node.id) focusRow(next.node.id)
      return
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault()
      if (row.hasChildren && expanded.has(row.node.id)) {
        toggle(row.node.id)
        return
      }
      if (row.parentId) focusRow(row.parentId)
    }
  }

  return (
    <ul
      role="tree"
      aria-label="知识点目录"
      className={cn("space-y-px", className)}
    >
      {filteredTree.map((node) => (
        <TreeRow
          key={node.id}
          node={node}
          depth={0}
          parentId={null}
          value={value}
          counts={counts}
          expanded={expanded}
          focusableId={focusableId}
          rowRefs={rowRefs}
          selectedRef={selectedRef}
          onToggle={toggle}
          onSelect={onSelect}
          onFocusRow={setFocusedId}
          onKeyDown={handleKeyDown}
        />
      ))}
    </ul>
  )
}

function flattenRows(
  nodes: KnowledgePointTreeNode[],
  expanded: Set<string>,
  depth = 0,
  parentId: string | null = null,
): FlatRow[] {
  const rows: FlatRow[] = []
  for (const node of nodes) {
    const hasChildren = node.children.length > 0
    rows.push({ node, depth, parentId, hasChildren })
    if (hasChildren && expanded.has(node.id)) {
      rows.push(
        ...flattenRows(node.children, expanded, depth + 1, node.id),
      )
    }
  }
  return rows
}

function TreeRow({
  node,
  depth,
  parentId,
  value,
  counts,
  expanded,
  focusableId,
  rowRefs,
  selectedRef,
  onToggle,
  onSelect,
  onFocusRow,
  onKeyDown,
}: {
  node: KnowledgePointTreeNode
  depth: number
  parentId: string | null
  value?: string
  counts?: Record<string, number>
  expanded: Set<string>
  focusableId?: string
  rowRefs: RefObject<Map<string, HTMLButtonElement>>
  selectedRef: RefObject<HTMLButtonElement | null>
  onToggle: (id: string) => void
  onSelect: (id: string) => void
  onFocusRow: (id: string) => void
  onKeyDown: (
    event: KeyboardEvent<HTMLButtonElement>,
    row: FlatRow,
  ) => void
}) {
  const hasChildren = node.children.length > 0
  const open = expanded.has(node.id)
  const selected = node.id === value
  const count = counts?.[node.id] ?? 0
  const countLabel = hasChildren
    ? `${count} 题（含子知识点）`
    : `${count} 题`
  const accessibleLabel = counts
    ? `${node.id} ${node.title}，${countLabel}`
    : undefined

  return (
    <li
      role="treeitem"
      aria-level={depth + 1}
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
            tabIndex={-1}
            onClick={() => onToggle(node.id)}
            aria-label={`${open ? "收起" : "展开"} ${node.id} ${node.title}`}
            className="flex size-6 shrink-0 items-center justify-center rounded-sm text-ink-muted transition-colors hover:bg-surface-3 hover:text-ink focus-visible:ring-2 focus-visible:ring-ring/30"
          >
            <ChevronRight
              className={cn(
                "size-3.5 transition-transform",
                open && "rotate-90",
              )}
              aria-hidden="true"
            />
          </button>
        ) : (
          <span className="size-6 shrink-0" aria-hidden="true" />
        )}

        <button
          ref={(element) => {
            if (element) {
              rowRefs.current.set(node.id, element)
              if (selected) selectedRef.current = element
            } else {
              rowRefs.current.delete(node.id)
            }
          }}
          type="button"
          tabIndex={focusableId === node.id ? 0 : -1}
          onClick={() => onSelect(node.id)}
          onFocus={() => onFocusRow(node.id)}
          onKeyDown={(event) =>
            onKeyDown(event, {
              node,
              depth,
              parentId,
              hasChildren,
            })
          }
          aria-current={selected ? "true" : undefined}
          aria-label={accessibleLabel}
          className={cn(
            "flex min-w-0 flex-1 items-center gap-2 rounded-sm px-1.5 py-1 text-left transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/30",
            selected
              ? "bg-link-soft text-link-strong"
              : "text-ink-soft hover:bg-surface-2 hover:text-ink",
            counts !== undefined &&
              count === 0 &&
              "text-ink-muted/60",
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
          <span className="truncate text-[12px]" title={node.title}>
            {node.title}
          </span>
          {counts !== undefined ? (
            <span
              title={countLabel}
              className={cn(
                "ml-auto w-8 shrink-0 text-right font-mono text-[10px] tabular-nums",
                selected ? "text-link" : "text-ink-muted",
              )}
            >
              {count}
            </span>
          ) : selected ? (
            <Check
              className="ml-auto size-3.5 shrink-0 text-link"
              aria-hidden="true"
            />
          ) : null}
        </button>
      </div>

      {hasChildren && open && (
        <ul role="group" className="space-y-px">
          {node.children.map((child) => (
            <TreeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              parentId={node.id}
              value={value}
              counts={counts}
              expanded={expanded}
              focusableId={focusableId}
              rowRefs={rowRefs}
              selectedRef={selectedRef}
              onToggle={onToggle}
              onSelect={onSelect}
              onFocusRow={onFocusRow}
              onKeyDown={onKeyDown}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
