import { useEffect, useState } from "react"
import { ImageOff } from "lucide-react"

import { useInView } from "@/shared/lib/hooks"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog"
import { cn } from "@/shared/lib/utils"

import { fetchFileBlob, type FileVariant } from "../api"
import type { ImageMarker } from "../markers"

function useFileObjectUrl(
  fileId: string,
  variant: FileVariant,
  enabled = true,
): { url: string | null; failed: boolean; loading: boolean } {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const [loading, setLoading] = useState(enabled)

  useEffect(() => {
    if (!enabled) return

    let active = true
    let objectUrl: string | null = null
    const controller = new AbortController()
    setUrl(null)
    setFailed(false)
    setLoading(true)

    void (async () => {
      try {
        const blob = await fetchFileBlob(fileId, variant, controller.signal)
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      } catch {
        if (active && !controller.signal.aborted) setFailed(true)
      } finally {
        if (active) setLoading(false)
      }
    })()

    return () => {
      active = false
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [enabled, fileId, variant])

  return { url, failed, loading }
}

function RawImage({ fileId, name }: ImageMarker) {
  const { url, failed, loading } = useFileObjectUrl(fileId, "raw")

  if (loading) {
    return <p className="px-1 py-8 text-center text-[13px] text-ink-muted">图片加载中…</p>
  }
  if (failed || !url) {
    return <p className="px-1 py-8 text-center text-[13px] text-ink-muted">图片已删除</p>
  }
  return (
    <img
      src={url}
      alt={name}
      className="mx-auto block max-h-[78vh] w-auto max-w-full object-contain"
    />
  )
}

function UserImage({ fileId, name }: ImageMarker) {
  const [open, setOpen] = useState(false)
  const [thumbRef, inView] = useInView<HTMLButtonElement>()
  const { url, failed, loading } = useFileObjectUrl(
    fileId,
    "thumb",
    inView,
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <button
        ref={thumbRef}
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          "group relative size-32 overflow-hidden rounded-md border border-line bg-surface-3",
          "focus-visible:ring-2 focus-visible:ring-ring/35 focus-visible:outline-none sm:size-40",
        )}
        aria-label={`查看图片 ${name}`}
      >
        {url ? (
          <img
            src={url}
            alt={name}
            loading="lazy"
            className="size-full object-cover transition-transform duration-200 group-hover:scale-[1.03]"
          />
        ) : (
          <span className="flex size-full flex-col items-center justify-center gap-1 px-2 text-center text-[11px] text-ink-muted">
            <ImageOff className="size-4" aria-hidden="true" />
            {loading ? "加载中" : failed ? "图片已删除" : "图片"}
          </span>
        )}
      </button>
      <DialogContent className="max-w-[min(96vw,1100px)] p-3 sm:p-4">
        <DialogHeader>
          <DialogTitle className="truncate pr-8 text-sm">{name}</DialogTitle>
        </DialogHeader>
        <RawImage fileId={fileId} name={name} />
      </DialogContent>
    </Dialog>
  )
}

export function UserImages({ images }: { images: ImageMarker[] }) {
  if (images.length === 0) return null
  return (
    <div
      className={cn(
        "grid gap-2",
        images.length === 1 ? "max-w-[240px] grid-cols-1" : "grid-cols-2",
      )}
    >
      {images.map((image, index) => (
        <UserImage key={`${image.fileId}-${index}`} {...image} />
      ))}
    </div>
  )
}
