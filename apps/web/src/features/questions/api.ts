/** 题库 REST 客户端。鉴权、401 续期由 apiFetch 统一处理。 */

import { apiFetch } from "@/shared/api/client"
import type { components } from "@/shared/api/schema"
import type {
  KnowledgePointsResponse,
  QuestionDetail,
  QuestionFilters,
  QuestionInput,
  QuestionSearchResponse,
} from "@/shared/api/types"

import { PAGE_SIZE } from "./model"

export type QuestionCreateResult =
  components["schemas"]["QuestionCreateResponse"]

export function listQuestions(
  filters: QuestionFilters,
  signal?: AbortSignal,
): Promise<QuestionSearchResponse> {
  const params = new URLSearchParams({
    scope: filters.scope,
    limit: String(filters.limit ?? PAGE_SIZE),
    offset: String(filters.offset ?? 0),
  })

  const query = filters.query?.trim()
  if (query) params.set("query", query)
  if (filters.question_type) params.set("question_type", filters.question_type)
  if (filters.knowledge_point_id) {
    params.set("knowledge_point_id", filters.knowledge_point_id)
  }

  return apiFetch<QuestionSearchResponse>(
    `/question-bank/questions?${params.toString()}`,
    { signal },
  )
}

export function getQuestion(
  questionId: string,
  signal?: AbortSignal,
): Promise<QuestionDetail> {
  return apiFetch<QuestionDetail>(
    `/question-bank/questions/${encodeURIComponent(questionId)}`,
    { signal },
  )
}

export function getKnowledgePoints(
  signal?: AbortSignal,
): Promise<KnowledgePointsResponse> {
  return apiFetch<KnowledgePointsResponse>("/question-bank/knowledge-points", {
    signal,
  })
}

export function createQuestion(
  input: QuestionInput,
): Promise<QuestionCreateResult> {
  return apiFetch<QuestionCreateResult>("/question-bank/questions", {
    method: "POST",
    body: input,
  })
}

export function updateQuestion(
  questionId: string,
  input: QuestionInput,
): Promise<QuestionDetail> {
  return apiFetch<QuestionDetail>(
    `/question-bank/questions/${encodeURIComponent(questionId)}`,
    {
      method: "PUT",
      body: input,
    },
  )
}

export function deleteQuestion(questionId: string): Promise<void> {
  return apiFetch<void>(
    `/question-bank/questions/${encodeURIComponent(questionId)}`,
    { method: "DELETE" },
  )
}
