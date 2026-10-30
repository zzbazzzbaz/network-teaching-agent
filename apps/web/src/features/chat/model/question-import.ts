import { z } from "zod"

import {
  LETTERS,
  validateQuestionDraft,
  type QuestionEditorDraft,
} from "@/features/questions/model"
import type { QuestionInput } from "@/shared/api/types"

const draftSchema = z.object({
  mode: z.enum(["single_choice", "short_answer"]),
  stem: z.string().min(1).max(4000),
  options: z.array(z.string()).nullable().optional(),
  correct_option: z.string().nullable().optional(),
  reference_answer: z.string().nullable().optional(),
  primary_knowledge_point_id: z.string().min(1).max(16),
  secondary_knowledge_point_ids: z.array(z.string()).max(3).default([]),
})

const payloadSchema = z.object({
  type: z.literal("question_import"),
  questions: z.array(draftSchema).min(1).max(5),
})

export type ImportDraft = z.infer<typeof draftSchema>

export function parseImportPayload(value: unknown): ImportDraft[] | undefined {
  const parsed = payloadSchema.safeParse(value)
  return parsed.success ? parsed.data.questions : undefined
}

export function toEditorDraft(draft: ImportDraft): QuestionEditorDraft {
  const choice = draft.mode === "single_choice"
  const optionTexts = choice ? (draft.options ?? []) : []
  const correctIndex =
    choice && draft.correct_option
      ? LETTERS.findIndex((letter) => letter === draft.correct_option)
      : -1
  return {
    questionType: draft.mode,
    stem: draft.stem,
    optionTexts,
    correctIndex,
    referenceAnswer: choice ? "" : (draft.reference_answer ?? ""),
    primaryKnowledgePointId: draft.primary_knowledge_point_id,
    secondaryKnowledgePointIds: draft.secondary_knowledge_point_ids,
  }
}

export function fromQuestionInput(input: QuestionInput): ImportDraft {
  return {
    mode: input.question_type,
    stem: input.stem,
    options: input.options ?? null,
    correct_option: input.correct_option ?? null,
    reference_answer: input.reference_answer ?? null,
    primary_knowledge_point_id: input.primary_knowledge_point_id,
    secondary_knowledge_point_ids:
      input.secondary_knowledge_point_ids ?? [],
  }
}

export function toAgentQuestion(input: QuestionInput) {
  return {
    mode: input.question_type,
    stem: input.stem,
    options: input.options ?? null,
    correct_option: input.correct_option ?? null,
    reference_answer: input.reference_answer ?? null,
    primary_knowledge_point_id: input.primary_knowledge_point_id,
    secondary_knowledge_point_ids:
      input.secondary_knowledge_point_ids ?? [],
  }
}

export function validateImports(drafts: ImportDraft[]) {
  return drafts.map((draft) => validateQuestionDraft(toEditorDraft(draft)))
}

export function firstError(
  errors: Record<string, string | undefined>,
): string {
  return (
    Object.values(errors).find((value): value is string => Boolean(value)) ??
    "请检查题目内容。"
  )
}
