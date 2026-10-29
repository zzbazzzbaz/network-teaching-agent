import { API_BASE, authedFetch } from "@/shared/api/client"

export interface UploadedFile {
  file_id: string
  name: string
  mime: string
  size_bytes: number
  created_at: string
}

export type FileVariant = "raw" | "thumb"

async function responseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === "string" && payload.detail) {
      return payload.detail
    }
  } catch {
    // 非 JSON 响应
  }
  return `请求失败（HTTP ${response.status}）`
}

export async function uploadImage(file: File): Promise<UploadedFile> {
  const form = new FormData()
  form.append("file", file)
  const response = await authedFetch(`${API_BASE}/files`, {
    method: "POST",
    body: form,
  })
  if (!response.ok) {
    throw new Error(await responseError(response))
  }
  return (await response.json()) as UploadedFile
}

export async function fetchFileBlob(
  fileId: string,
  variant: FileVariant,
  signal?: AbortSignal,
): Promise<Blob> {
  const response = await authedFetch(`${API_BASE}/files/${fileId}/${variant}`, {
    signal,
  })
  if (!response.ok) {
    throw new Error(await responseError(response))
  }
  return response.blob()
}
