import type { AppendMessage } from "@assistant-ui/react"

export type MessageAttachment = {
  file_id: string
  name: string
  mime: string
  base64: string
}

export function messageText(message: AppendMessage): string {
  return message.content
    .filter(
      (part): part is { type: "text"; text: string } => part.type === "text",
    )
    .map((part) => part.text)
    .join("\n")
    .trim()
}

export function messageAttachments(
  message: AppendMessage,
): MessageAttachment[] {
  return (message.attachments ?? []).map((attachment) => ({
    file_id: attachment.id,
    name: attachment.name,
    mime: attachment.contentType ?? "",
    base64: attachmentBase64(attachment),
  }))
}

/** 上传时把原始图片以 data URL 存进附件 content，发送时再取回 base64。 */
function attachmentBase64(attachment: {
  content?: readonly { type: string; image?: string }[]
}): string {
  for (const part of attachment.content ?? []) {
    if (part.type !== "image" || !part.image) continue
    const comma = part.image.indexOf(",")
    if (comma >= 0) return part.image.slice(comma + 1)
  }
  return ""
}

/**
 * 首条消息和普通消息共用同一种载荷：正文带 marker 供学生端渲染，
 * 图片按 LangChain 标准 image 块随消息发出，由 Agent 侧卸载到 /blobs/。
 */
export function buildHumanMessage(
  text: string,
  attachments: MessageAttachment[],
) {
  const body = [
    text,
    ...attachments.map(
      (attachment) =>
        `[图片] ${attachment.name} (file_id=${attachment.file_id})`,
    ),
  ]
    .filter(Boolean)
    .join("\n\n")

  const images = attachments
    .filter((attachment) => attachment.base64)
    .map((attachment) => ({
      type: "image" as const,
      base64: attachment.base64,
      mime_type: attachment.mime,
    }))

  return {
    type: "human" as const,
    id: crypto.randomUUID(),
    content:
      images.length > 0
        ? [...(body ? [{ type: "text" as const, text: body }] : []), ...images]
        : body,
  }
}

const MEDIA_PART_TYPES = new Set([
  "image",
  "image_url",
  "file",
  "audio",
  "video",
])

/**
 * 学生端只渲染文本里的图片 marker：历史消息里的图片块可能还是 base64，
 * 也可能已被 Agent 换成 deepagents_blob 摘要，两者都不该进浏览器。
 */
export function stripMediaParts<T extends { content: unknown }>(
  message: T,
): T {
  if (!Array.isArray(message.content)) return message

  const content = message.content.filter(
    (part) =>
      !(
        part &&
        typeof part === "object" &&
        "type" in part &&
        MEDIA_PART_TYPES.has(String(part.type))
      ),
  )
  if (content.length === message.content.length) return message
  return { ...message, content } as T
}
