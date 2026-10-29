import {
  MessagePrimitive,
  useAuiState,
  type TextMessagePartComponent,
  type ToolCallMessagePartComponent,
} from "@assistant-ui/react"

import { parseImageMarkers } from "@/features/files/markers"
import { UserImages } from "@/features/files/ui/UserImages"
import { cn } from "@/shared/lib/utils"

import { MarkdownText } from "./markdown"
import { ToolCallCard } from "./ToolCallCard"

const UserText: TextMessagePartComponent = ({ text }) => {
  const parsed = parseImageMarkers(text)
  if (parsed.images.length === 0) {
    return <p className="whitespace-pre-wrap">{text}</p>
  }
  return (
    <div className="flex flex-col gap-2">
      {parsed.text && <p className="whitespace-pre-wrap">{parsed.text}</p>}
      <UserImages images={parsed.images} />
    </div>
  )
}

const ToolPart: ToolCallMessagePartComponent = (props) => (
  <ToolCallCard {...props} />
)

export function UserMessage() {
  return (
    <MessagePrimitive.Root className="thread-message relative flex justify-end pl-0">
      <div className="ml-auto w-fit max-w-[86%] rounded-lg border border-line bg-surface-2 px-3.5 py-2.5 text-[14px] leading-7 break-words text-ink">
        <MessagePrimitive.Parts components={{ Text: UserText }} />
      </div>
    </MessagePrimitive.Root>
  )
}

export function AssistantMessage() {
  const streaming = useAuiState(
    (state) =>
      state.message.status?.type === "running" ||
      state.message.status?.type === "incomplete",
  )

  return (
    <MessagePrimitive.Root className="thread-message relative min-w-0 pl-7 lg:pl-8">
      <span
        aria-hidden="true"
        className={cn(
          "message-trace absolute top-4 bottom-0 left-[3px] w-px trace-line",
        )}
      />
      <span
        aria-hidden="true"
        className={cn(
          "absolute top-2 left-0 size-[7px] rounded-full bg-link ring-2 ring-surface",
          streaming && "link-pulse",
        )}
      />
      <div className={cn("flex min-w-0 flex-col gap-3", streaming && "streaming-caret")}>
        <MessagePrimitive.Parts
          components={{
            Text: MarkdownText,
            tools: { Fallback: ToolPart },
          }}
        />
      </div>
    </MessagePrimitive.Root>
  )
}
