/** TanStack Query：题库列表、详情与增删改。 */

import {
  infiniteQueryOptions,
  keepPreviousData,
  queryOptions,
  useInfiniteQuery,
  useMutation,
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
  getKnowledgePointCounts,
  getQuestion,
  getQuestionAttempts,
  listQuestions,
  updateQuestion,
} from "./api"
import {
  ATTEMPT_PAGE_SIZE,
  PAGE_SIZE,
  type QuestionFilterState,
  type TypeFilter,
} from "./model"

export const questionKeys = {
  all: ["question-bank"] as const,
  lists: () => [...questionKeys.all, "list"] as const,
  list: (scope: QuestionScope, filters: QuestionFilterState) =>
    [...questionKeys.lists(), scope, filters] as const,
  knowledgePointCountsRoot: () =>
    [...questionKeys.all, "knowledge-point-counts"] as const,
  knowledgePointCounts: (filters: KnowledgePointCountFilters) =>
    [...questionKeys.knowledgePointCountsRoot(), filters] as const,
  details: () => [...questionKeys.all, "detail"] as const,
  detail: (questionId: string) =>
    [...questionKeys.details(), questionId] as const,
  attempts: (questionId: string) =>
    [...questionKeys.all, "attempts", questionId] as const,
}

export type KnowledgePointCountFilters = {
  query: string
  questionType: TypeFilter
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
    knowledge_point_match:
      filters.knowledgePointId === "all" ? undefined : "primary",
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
  enabled = true,
) {
  return useInfiniteQuery({
    ...questionsQueryOptions(scope, filters),
    enabled,
  })
}

export function knowledgePointCountsQueryOptions(
  filters: KnowledgePointCountFilters,
) {
  return queryOptions({
    queryKey: questionKeys.knowledgePointCounts(filters),
    queryFn: ({ signal }) =>
      getKnowledgePointCounts(
        {
          query: filters.query || undefined,
          question_type:
            filters.questionType === "all" ? undefined : filters.questionType,
        },
        signal,
      ),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  })
}

export function useKnowledgePointCounts(
  filters: KnowledgePointCountFilters,
) {
  return useQuery(knowledgePointCountsQueryOptions(filters))
}

export function questionDetailQueryOptions(questionId: string) {
  return queryOptions({
    queryKey: questionKeys.detail(questionId),
    queryFn: ({ signal }) => getQuestion(questionId, signal),
    staleTime: 15_000,
  })
}

export function questionAttemptsQueryOptions(questionId: string) {
  return infiniteQueryOptions({
    queryKey: questionKeys.attempts(questionId),
    queryFn: ({ pageParam, signal }) =>
      getQuestionAttempts(
        questionId,
        { limit: ATTEMPT_PAGE_SIZE, offset: pageParam },
        signal,
      ),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const next = lastPage.offset + lastPage.items.length
      return next < lastPage.total ? next : undefined
    },
    staleTime: 0,
  })
}

export function useQuestionAttempts(questionId: string, enabled = true) {
  return useInfiniteQuery({
    ...questionAttemptsQueryOptions(questionId),
    enabled,
  })
}

function invalidateQuestionLists(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: questionKeys.lists() })
  void queryClient.invalidateQueries({
    queryKey: questionKeys.knowledgePointCountsRoot(),
  })
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
