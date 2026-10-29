import { apiFetch } from "@/shared/api/client"
import type { MemoryEntry, MemoryFile } from "@/shared/api/types"

export interface MemoryTreeResponse {
  entries: MemoryEntry[]
}

export function fetchMemoryTree(): Promise<MemoryTreeResponse> {
  return apiFetch<MemoryTreeResponse>("/memory/tree")
}

export function fetchMemoryFile(path: string): Promise<MemoryFile> {
  const params = new URLSearchParams({ path })
  return apiFetch<MemoryFile>(`/memory/file?${params.toString()}`)
}
