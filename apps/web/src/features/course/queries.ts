import { queryOptions, useQuery } from "@tanstack/react-query"
import { useMemo } from "react"

import { getCourseOutline } from "./api"
import { buildCourseOutline } from "./model"

export const courseKeys = {
  outline: () => ["course", "outline"] as const,
}

export function courseOutlineQueryOptions() {
  return queryOptions({
    queryKey: courseKeys.outline(),
    queryFn: ({ signal }) => getCourseOutline(signal),
    // 教材目录一个学期不变，和题库树共用同一份缓存数据。
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 30 * 60_000,
  })
}

export function useKnowledgePoints(enabled = true) {
  return useQuery({ ...courseOutlineQueryOptions(), enabled })
}

export function useCourseOutline(enabled = true) {
  const query = useKnowledgePoints(enabled)
  const outline = useMemo(
    () => buildCourseOutline(query.data?.nodes ?? []),
    [query.data],
  )
  return { ...query, outline }
}
