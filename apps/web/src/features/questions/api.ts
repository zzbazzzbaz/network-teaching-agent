/** 题库 REST 客户端。鉴权、401 续期由 apiFetch 统一处理。 */

import { apiFetch } from "@/shared/api/client"
import type { components } from "@/shared/api/schema"
import type {
  KnowledgePointCounts,
  QuestionDetail,
  QuestionFilters,
  QuestionInput,
  QuestionSearchResponse,
  QuestionType,
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
  if (filters.knowledge_point_prefix) {
    params.set("knowledge_point_prefix", filters.knowledge_point_prefix)
  }
  if (filters.knowledge_point_match) {
    params.set("knowledge_point_match", filters.knowledge_point_match)
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

export function getKnowledgePointCounts(
  filters: { query?: string; question_type?: QuestionType },
  signal?: AbortSignal,
): Promise<KnowledgePointCounts> {
  const params = new URLSearchParams()
  const query = filters.query?.trim()
  if (query) params.set("query", query)
  if (filters.question_type) params.set("question_type", filters.question_type)
  const queryString = params.toString()
  const suffix = queryString ? `?${queryString}` : ""
  return apiFetch<KnowledgePointCounts>(
    `/question-bank/knowledge-points/counts${suffix}`,
    { signal },
  )
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
