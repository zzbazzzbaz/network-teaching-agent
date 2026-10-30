import type { AppendMessage } from "@assistant-ui/react"

export type MessageAttachment = {
  file_id: string
  name: string
  mime: string
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
  }))
}

/** 首条消息和普通消息共用同一种载荷，图片只带 file_id。 */
export function buildHumanMessage(
  text: string,
  attachments: MessageAttachment[],
) {
  const markers = attachments.map(
    (attachment) =>
      `[图片] ${attachment.name} (file_id=${attachment.file_id})`,
  )
  return {
    type: "human" as const,
    id: crypto.randomUUID(),
    content: [text, ...markers].filter(Boolean).join("\n\n"),
    additional_kwargs: { attachments },
  }
}
