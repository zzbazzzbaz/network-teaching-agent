import { useMemo } from "react"
import type { ToolCallMessagePartProps } from "@assistant-ui/react"

import { parseAnswerArtifact } from "../../model/tool-call"
import { GenericToolCard } from "./GenericToolCard"
import { StudentAnswerCard } from "./StudentAnswerCard"

/**
 * practice_question 完成后的富卡片。题目、学生答案和参考答案都来自
 * Agent 工具返回的 artifact；旧会话没有 artifact 时回退通用卡片。
 */
export function PracticeQuestionResult(props: ToolCallMessagePartProps) {
  const artifact = useMemo(
    () => parseAnswerArtifact(props.artifact),
    [props.artifact],
  )

  if (!artifact) {
    return <GenericToolCard {...props} />
  }

  return (
    <StudentAnswerCard
      question={artifact.question}
      student={artifact.student}
      reference={artifact.reference}
      warning={artifact.warning}
    />
  )
}
