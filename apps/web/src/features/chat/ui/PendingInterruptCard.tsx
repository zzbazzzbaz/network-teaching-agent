import type { ChatStream } from "../model/useChatSession"
import { AskStudentCard } from "./AskStudentCard"
import { QuestionImportCard } from "./QuestionImportCard"

function interruptType(value: unknown): string | undefined {
  if (!value || typeof value !== "object") return undefined
  const type = (value as Record<string, unknown>).type
  return typeof type === "string" ? type : undefined
}

export function PendingInterruptCard({
  pending,
  stream,
}: {
  pending: { id?: string; value?: unknown }
  stream: ChatStream
}) {
  if (interruptType(pending.value) === "question_import") {
    return <QuestionImportCard interrupt={pending} stream={stream} />
  }
  return <AskStudentCard interrupt={pending} stream={stream} />
}
