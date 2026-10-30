import type { ToolCallMessagePartComponent } from "@assistant-ui/react"

import { AskStudentResult } from "./tool/AskStudentResult"
import { GenericToolCard } from "./tool/GenericToolCard"
import { ImportQuestionsResult } from "./tool/ImportQuestionsResult"
import { PracticeQuestionResult } from "./tool/PracticeQuestionResult"

/** 工具调用展示的分发器；具体解析和视图在 tool/ 下。 */
export const ToolCallCard: ToolCallMessagePartComponent = (props) => {
  const { toolName, status, isError } = props

  if (toolName === "ask_student") {
    if (status.type === "running" || status.type === "requires-action") {
      return null
    }
    if (isError) return null
    return <AskStudentResult {...props} />
  }

  if (toolName === "practice_question") {
    if (status.type === "running" || status.type === "requires-action") {
      return null
    }
    return <PracticeQuestionResult {...props} />
  }

  if (toolName === "import_questions") {
    if (status.type === "running" || status.type === "requires-action") {
      return null
    }
    return (
      <ImportQuestionsResult result={props.result} isError={isError} />
    )
  }

  return <GenericToolCard {...props} />
}
