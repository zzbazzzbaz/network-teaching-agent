/** TanStack Query：题库列表、详情、知识点与增删改。 */

import {
  infiniteQueryOptions,
  queryOptions,
  useInfiniteQuery,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"

import { ApiError } from "@/shared/api/client"
import type {
  QuestionFilters,
  QuestionInput,
  QuestionScope,
} from "@/shared/api/types"

import {
  createQuestion,
  deleteQuestion,
  getKnowledgePoints,
  getQuestion,
  listQuestions,
  updateQuestion,
} from "./api"
import {
  PAGE_SIZE,
  SCOPE_OPTIONS,
  type QuestionFilterState,
} from "./model"

export const questionKeys = {
  all: ["question-bank"] as const,
  lists: () => [...questionKeys.all, "list"] as const,
  list: (scope: QuestionScope, filters: QuestionFilterState) =>
    [...questionKeys.lists(), scope, filters] as const,
  counts: () => [...questionKeys.all, "count"] as const,
  count: (scope: QuestionScope, filters: QuestionFilterState) =>
    [...questionKeys.counts(), scope, filters] as const,
  details: () => [...questionKeys.all, "detail"] as const,
  detail: (questionId: string) =>
    [...questionKeys.details(), questionId] as const,
  knowledgePoints: () => [...questionKeys.all, "knowledge-points"] as const,
}

function toApiFilters(
  scope: QuestionScope,
  filters: QuestionFilterState,
  limit: number,
  offset: number,
): QuestionFilters {
  return {
    scope,
    limit,
    offset,
    query: filters.query.trim() || undefined,
    question_type:
      filters.questionType === "all" ? undefined : filters.questionType,
    knowledge_point_prefix:
      filters.knowledgePointId === "all" ? undefined : filters.knowledgePointId,
  }
}

export function questionsQueryOptions(
  scope: QuestionScope,
  filters: QuestionFilterState,
) {
  return infiniteQueryOptions({
    queryKey: questionKeys.list(scope, filters),
    queryFn: ({ pageParam, signal }) =>
      listQuestions(
        toApiFilters(scope, filters, PAGE_SIZE, pageParam),
        signal,
      ),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const next = lastPage.offset + lastPage.items.length
      return next < lastPage.total ? next : undefined
    },
  })
}

export function useQuestions(
  scope: QuestionScope,
  filters: QuestionFilterState,
) {
  return useInfiniteQuery(questionsQueryOptions(scope, filters))
}

export type QuestionCounts = Partial<Record<QuestionScope, number>>

/**
 * 后端没有 count 接口，用每个 scope 的 limit=1 查询拿到 total。
 * 计数跟随除 scope 以外的筛选条件。
 */
export function useQuestionCounts(
  filters: QuestionFilterState,
): QuestionCounts {
  const results = useQueries({
    queries: SCOPE_OPTIONS.map((scope) =>
      queryOptions({
        queryKey: questionKeys.count(scope.id, filters),
        queryFn: ({ signal }) =>
          listQuestions(toApiFilters(scope.id, filters, 1, 0), signal),
        staleTime: 30_000,
      }),
    ),
  })

  const counts: QuestionCounts = {}
  SCOPE_OPTIONS.forEach((scope, index) => {
    const total = results[index]?.data?.total
    if (typeof total === "number") counts[scope.id] = total
  })
  return counts
}

export function knowledgePointsQueryOptions() {
  return queryOptions({
    queryKey: questionKeys.knowledgePoints(),
    queryFn: ({ signal }) => getKnowledgePoints(signal),
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 30 * 60_000,
  })
}

export function useKnowledgePoints() {
  return useQuery(knowledgePointsQueryOptions())
}

export function questionDetailQueryOptions(questionId: string) {
  return queryOptions({
    queryKey: questionKeys.detail(questionId),
    queryFn: ({ signal }) => getQuestion(questionId, signal),
    staleTime: 15_000,
  })
}

function invalidateQuestionLists(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: questionKeys.lists() })
  void queryClient.invalidateQueries({ queryKey: questionKeys.counts() })
}

export function useCreateQuestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: QuestionInput) => createQuestion(input),
    onSuccess: () => {
      invalidateQuestionLists(queryClient)
    },
  })
}

export function useUpdateQuestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      questionId,
      input,
    }: {
      questionId: string
      input: QuestionInput
    }) => updateQuestion(questionId, input),
    onSuccess: (detail) => {
      queryClient.setQueryData(questionKeys.detail(detail.question_id), detail)
      invalidateQuestionLists(queryClient)
    },
    onError: (error, variables) => {
      // 题目已在别处被删除：清掉缓存，让列表跟上。
      if (error instanceof ApiError && error.status === 404) {
        queryClient.removeQueries({
          queryKey: questionKeys.detail(variables.questionId),
        })
        invalidateQuestionLists(queryClient)
      }
    },
  })
}

export function useDeleteQuestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (questionId: string) => deleteQuestion(questionId),
    onSuccess: (_result, questionId) => {
      queryClient.removeQueries({ queryKey: questionKeys.detail(questionId) })
      invalidateQuestionLists(queryClient)
    },
    onError: (error, questionId) => {
      // 题目已在别处被删除：清掉缓存，让列表跟上。
      if (error instanceof ApiError && error.status === 404) {
        queryClient.removeQueries({ queryKey: questionKeys.detail(questionId) })
        invalidateQuestionLists(queryClient)
      }
    },
  })
}
