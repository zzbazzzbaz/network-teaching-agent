import { toast } from "sonner"
import type {
  AttachmentAdapter,
  CompleteAttachment,
  PendingAttachment,
} from "@assistant-ui/react"

import { uploadImage } from "./api"

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"]
// 图片以 base64 随消息经 nginx 发往 Agent（client_max_body_size 20m），
// 单张 4MB 时三张约 16MB，留出 JSON 与历史消息的余量。
const MAX_IMAGE_BYTES = 4 * 1024 * 1024

function readDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ""))
    reader.onerror = () => reject(new Error("读取图片失败"))
    reader.readAsDataURL(file)
  })
}

export class ImageAttachmentAdapter implements AttachmentAdapter {
  accept = ACCEPTED_TYPES.join(",")

  async add({ file }: { file: File }): Promise<PendingAttachment> {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      const message = "只支持 JPEG、PNG、WebP 图片"
      toast.error(message)
      throw new Error(message)
    }
    if (file.size > MAX_IMAGE_BYTES) {
      const message = "图片不能超过 4MB"
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
      const [uploaded, dataUrl] = await Promise.all([
        uploadImage(attachment.file),
        readDataUrl(attachment.file),
      ])
      return {
        id: uploaded.file_id,
        type: "image",
        name: uploaded.name,
        contentType: uploaded.mime,
        content: [{ type: "image", image: dataUrl }],
        status: { type: "complete" },
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "图片上传失败")
      throw error
    }
  }

  async remove(): Promise<void> {}
}
