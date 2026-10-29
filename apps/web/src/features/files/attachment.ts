import { toast } from "sonner"
import type {
  AttachmentAdapter,
  CompleteAttachment,
  PendingAttachment,
} from "@assistant-ui/react"

import { uploadImage } from "./api"

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"]
const MAX_IMAGE_BYTES = 10 * 1024 * 1024

export class ImageAttachmentAdapter implements AttachmentAdapter {
  accept = ACCEPTED_TYPES.join(",")

  async add({ file }: { file: File }): Promise<PendingAttachment> {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      const message = "只支持 JPEG、PNG、WebP 图片"
      toast.error(message)
      throw new Error(message)
    }
    if (file.size > MAX_IMAGE_BYTES) {
      const message = "图片不能超过 10MB"
      toast.error(message)
      throw new Error(message)
    }
    return {
      id: crypto.randomUUID(),
      type: "image",
      name: file.name,
      contentType: file.type,
      file,
      status: { type: "requires-action", reason: "composer-send" },
    }
  }

  async send(attachment: PendingAttachment): Promise<CompleteAttachment> {
    try {
      const uploaded = await uploadImage(attachment.file)
      return {
        id: uploaded.file_id,
        type: "image",
        name: uploaded.name,
        contentType: uploaded.mime,
        content: [{ type: "text", text: uploaded.name }],
        status: { type: "complete" },
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "图片上传失败")
      throw error
    }
  }

  async remove(): Promise<void> {}
}
