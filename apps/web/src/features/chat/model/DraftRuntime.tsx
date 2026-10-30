import {
  AssistantRuntimeProvider,
  useExternalStoreRuntime,
  type AppendMessage,
  type ThreadMessageLike,
} from "@assistant-ui/react"
import { useMemo, type ReactNode } from "react"

import { ImageAttachmentAdapter } from "@/features/files/attachment"

const EMPTY_MESSAGES: ThreadMessageLike[] = []

/**
 * 草稿态聊天运行时：没有 thread、没有 session，
 * 只负责让 Composer（含图片上传）可用，发送后交给首页去建会话。
 */
export function DraftRuntime({
  disabled = false,
  onNew,
  children,
}: {
  disabled?: boolean
  onNew: (message: AppendMessage) => Promise<void>
  children: ReactNode
}) {
  const attachmentAdapter = useMemo(() => new ImageAttachmentAdapter(), [])
  const runtime = useExternalStoreRuntime<ThreadMessageLike>({
    messages: EMPTY_MESSAGES,
    isRunning: false,
    isDisabled: disabled,
    adapters: { attachments: attachmentAdapter },
    onNew,
    convertMessage: (message) => message,
  })

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  )
}
