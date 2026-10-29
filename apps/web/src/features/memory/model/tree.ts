import type { MemoryEntry } from "@/shared/api/types"

export const MEMORY_ROOT = "/memory/"
export const DEFAULT_MEMORY_FILE = "/memory/profile.md"

export interface MemoryTreeNode {
  path: string
  name: string
  kind: MemoryEntry["kind"]
  size: number
  modifiedAt: string | null
  children: MemoryTreeNode[]
}

function nameFromPath(path: string): string {
  const trimmed = path.endsWith("/") ? path.slice(0, -1) : path
  return trimmed.slice(trimmed.lastIndexOf("/") + 1)
}

export function parentDirectory(path: string): string | null {
  const trimmed = path.endsWith("/") ? path.slice(0, -1) : path
  const index = trimmed.lastIndexOf("/")
  if (index <= 0) return null
  return trimmed.slice(0, index + 1)
}

function ancestorDirectories(path: string): string[] {
  const relative = path.slice(MEMORY_ROOT.length)
  const segments = relative.split("/").filter(Boolean)
  const depth = path.endsWith("/") ? segments.length : segments.length - 1
  const directories = [MEMORY_ROOT]
  let current = MEMORY_ROOT
  for (let index = 0; index < depth; index += 1) {
    current = `${current}${segments[index]}/`
    directories.push(current)
  }
  return directories
}

function createDirectory(path: string): MemoryTreeNode {
  return {
    path,
    name: path === MEMORY_ROOT ? "memory" : nameFromPath(path),
    kind: "directory",
    size: 0,
    modifiedAt: null,
    children: [],
  }
}

function sortTree(nodes: MemoryTreeNode[]): MemoryTreeNode[] {
  nodes.sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "directory" ? -1 : 1
    return a.name.localeCompare(b.name, "zh-CN")
  })
  for (const node of nodes) sortTree(node.children)
  return nodes
}

/** 后端返回扁平条目，这里按路径还原成可折叠目录树。 */
export function buildMemoryTree(
  entries: readonly MemoryEntry[],
): MemoryTreeNode[] {
  const nodes = new Map<string, MemoryTreeNode>()
  const root = createDirectory(MEMORY_ROOT)
  nodes.set(MEMORY_ROOT, root)

  function ensureDirectory(path: string): MemoryTreeNode {
    if (path === MEMORY_ROOT) return root
    const existing = nodes.get(path)
    if (existing) return existing
    const node = createDirectory(path)
    nodes.set(path, node)
    return node
  }

  for (const entry of entries) {
    const path =
      entry.kind === "directory" && !entry.path.endsWith("/")
        ? `${entry.path}/`
        : entry.path
    if (!path.startsWith(MEMORY_ROOT) || path === MEMORY_ROOT) continue

    for (const directory of ancestorDirectories(path)) {
      ensureDirectory(directory)
    }

    if (entry.kind === "directory") {
      const node = ensureDirectory(path)
      if (entry.name) node.name = entry.name
      node.modifiedAt = entry.modified_at
      continue
    }

    if (nodes.has(path)) continue
    nodes.set(path, {
      path,
      name: entry.name || nameFromPath(path),
      kind: "file",
      size: entry.size,
      modifiedAt: entry.modified_at,
      children: [],
    })
  }

  for (const node of nodes.values()) {
    if (node.path === MEMORY_ROOT) continue
    const parentPath = parentDirectory(node.path) ?? MEMORY_ROOT
    const parent = ensureDirectory(parentPath)
    if (!parent.children.includes(node)) parent.children.push(node)
  }

  return sortTree(root.children)
}
