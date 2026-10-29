import { useEffect, useState } from "react"
import {
  AttachmentPrimitive,
  type Attachment,
} from "@assistant-ui/react"
import { ImageOff, Loader2, X } from "lucide-react"

import { cn } from "@/shared/lib/utils"

function usePreviewUrl(file: File | undefined): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setUrl(null)
      return
    }
    const next = URL.createObjectURL(file)
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [file])

  return url
}

export function ComposerImagePreview({ attachment }: { attachment: Attachment }) {
  const url = usePreviewUrl(attachment.file)
  const failed = attachment.status.type === "incomplete"
  const uploading = attachment.status.type === "running"

  return (
    <AttachmentPrimitive.Root
      className={cn(
        "relative size-16 overflow-hidden rounded-md border bg-surface-3",
        failed ? "border-danger-line" : "border-line",
      )}
      title={attachment.name}
    >
      {url ? (
        <img src={url} alt={attachment.name} className="size-full object-cover" />
      ) : (
        <span className="flex size-full items-center justify-center text-ink-muted">
          <ImageOff className="size-4" aria-hidden="true" />
        </span>
      )}
      {uploading && (
        <span className="absolute inset-0 flex items-center justify-center bg-surface/55">
          <Loader2 className="size-4 animate-spin text-ink-soft" aria-hidden="true" />
        </span>
      )}
      <AttachmentPrimitive.Remove
        aria-label={`移除 ${attachment.name}`}
        className="absolute top-1 right-1 flex size-5 items-center justify-center rounded-full bg-ink/65 text-white transition-colors hover:bg-ink focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <X className="size-3" aria-hidden="true" />
      </AttachmentPrimitive.Remove>
    </AttachmentPrimitive.Root>
  )
}
