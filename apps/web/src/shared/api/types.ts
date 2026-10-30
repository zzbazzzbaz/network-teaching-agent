import type { components } from "./schema"

export type AuthResponse = components["schemas"]["AuthResponse"]
export type UserResponse = components["schemas"]["UserResponse"]
export type Session = components["schemas"]["SessionResponse"]
export type SessionPage = components["schemas"]["SessionPageResponse"]
export type AgentId = Session["agent_id"]
export type Mode = "learn" | "lab"

export type Sandbox = components["schemas"]["SandboxResponse"]
export type SandboxStatus = Sandbox["status"]
export type MemoryEntry = components["schemas"]["MemoryEntry"]
export type MemoryFile = components["schemas"]["MemoryFileResponse"]
export type KnowledgePoint = components["schemas"]["KnowledgePointNode"]
export type KnowledgePointsResponse = components["schemas"]["KnowledgePointsResponse"]
export type QuestionDetail = components["schemas"]["QuestionDetailResponse"]
export type QuestionInput = components["schemas"]["QuestionCreateRequest"]
export type QuestionType = QuestionInput["question_type"]
export type QuestionScope = "all" | "public" | "mine"
export type QuestionKnowledgePointMatch = "any" | "primary"

export type KnowledgePointCounts = {
  totals: Record<QuestionScope, number>
  counts: Record<QuestionScope, Record<string, number>>
}

/**
 * 列表接口的 summary 形态由后端动态裁字段，OpenAPI 只能描述为 object。
 * 这里按 P0 契约手写最小边界类型，详情仍使用生成的 DTO。
 */
export type QuestionSummary = {
  question_id: string
  origin: "public" | "mine"
  question_type: QuestionType
  stem_preview: string
  primary_knowledge_point: components["schemas"]["KnowledgePointRef"]
  secondary_knowledge_points: components["schemas"]["KnowledgePointRef"][]
  last_attempt_at: string | null
}

export type QuestionSearchResponse = {
  items: QuestionSummary[]
  total: number
  limit: number
  offset: number
}

export type QuestionAttemptItem = {
  attempt_id: string
  answer_text: string
  created_at: string
  thread_id: string | null
  session_title: string | null
  agent_id: AgentId | null
  session_exists: boolean
}

export type QuestionAttemptListResponse = {
  items: QuestionAttemptItem[]
  total: number
  limit: number
  offset: number
}

export type QuestionFilters = {
  scope: QuestionScope
  query?: string
  question_type?: QuestionType
  /**
   * 目录编号前缀：选中「5.8」会命中 5.8、5.8.1、5.8.2、5.8.3。
   * 题库树固定搭配 knowledge_point_match="primary"，只匹配主知识点。
   */
  knowledge_point_prefix?: string
  knowledge_point_match?: QuestionKnowledgePointMatch
  limit?: number
  offset?: number
}
