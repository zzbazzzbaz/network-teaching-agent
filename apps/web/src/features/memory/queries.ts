import { useQuery } from "@tanstack/react-query"

import { fetchMemoryFile, fetchMemoryTree } from "./api"

export const memoryKeys = {
  all: ["memory"] as const,
  tree: ["memory", "tree"] as const,
  file: (path: string) => ["memory", "file", path] as const,
}

export function useMemoryTree() {
  return useQuery({
    queryKey: memoryKeys.tree,
    queryFn: fetchMemoryTree,
    staleTime: 30_000,
  })
}

export function useMemoryFile(path: string | undefined) {
  return useQuery({
    queryKey: memoryKeys.file(path ?? ""),
    queryFn: () => fetchMemoryFile(path ?? ""),
    enabled: Boolean(path),
    staleTime: 30_000,
  })
}
