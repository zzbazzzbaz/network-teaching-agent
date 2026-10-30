/** 课程目录（教材章节）。当前复用题库的只读知识点接口。 */

import { apiFetch } from "@/shared/api/client"
import type { KnowledgePointsResponse } from "@/shared/api/types"

export function getCourseOutline(
  signal?: AbortSignal,
): Promise<KnowledgePointsResponse> {
  return apiFetch<KnowledgePointsResponse>("/question-bank/knowledge-points", {
    signal,
  })
}
