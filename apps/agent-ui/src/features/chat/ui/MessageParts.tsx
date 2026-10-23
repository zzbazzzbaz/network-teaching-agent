import {
  MessagePrimitive,
  type TextMessagePartComponent,
  type ToolCallMessagePartComponent,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import remarkGfm from "remark-gfm";

import { ToolCallCard } from "./ToolCallCard";

const PlainText: TextMessagePartComponent = ({ text }) => (
  <div className="text-part">{text}</div>
);

const MarkdownText: TextMessagePartComponent = () => (
  <MarkdownTextPrimitive
    className="text-part markdown"
    remarkPlugins={[remarkGfm]}
    defer
  />
);

const ToolPart: ToolCallMessagePartComponent = (props) => (
  <ToolCallCard {...props} />
);

export function UserMessage() {
  return (
    <MessagePrimitive.Root
      className="message message-user"
      data-testid="message-user"
    >
      <MessagePrimitive.Parts components={{ Text: PlainText }} />
    </MessagePrimitive.Root>
  );
}

export function AssistantMessage() {
  return (
    <MessagePrimitive.Root
      className="message message-assistant"
      data-testid="message-assistant"
    >
      <MessagePrimitive.Parts
        components={{
          Text: MarkdownText,
          tools: { Fallback: ToolPart },
        }}
      />
    </MessagePrimitive.Root>
  );
}
