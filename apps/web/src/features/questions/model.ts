/** 题库展示层的常量、文案和纯函数。 */

import { ApiError } from "@/shared/api/client"
import type {
  KnowledgePoint,
  QuestionDetail,
  QuestionInput,
  QuestionScope,
  QuestionType,
} from "@/shared/api/types"

export const PAGE_SIZE = 12
export const ATTEMPT_PAGE_SIZE = 10
export const MIN_OPTIONS = 2
export const MAX_OPTIONS = 6
export const STEM_MAX_LENGTH = 4000
export const REFERENCE_MAX_LENGTH = 8000
export const ALL_KNOWLEDGE_POINTS = "all"

export const LETTERS = ["A", "B", "C", "D", "E", "F"] as const

export const SCOPE_OPTIONS = [
  { id: "all", label: "全部" },
  { id: "public", label: "公共" },
  { id: "mine", label: "我的" },
] as const satisfies readonly { id: QuestionScope; label: string }[]

export const TYPE_OPTIONS = [
  { id: "all", label: "全部" },
  { id: "single_choice", label: "单选" },
  { id: "short_answer", label: "简答" },
] as const

export type TypeFilter = (typeof TYPE_OPTIONS)[number]["id"]

export type QuestionFilterState = {
  query: string
  questionType: TypeFilter
  knowledgePointId: string
}

const TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: "单选",
  short_answer: "简答",
}

export function typeLabel(type: QuestionType): string {
  return TYPE_LABELS[type]
}

export function originLabel(origin: "public" | "mine"): string {
  return origin === "public" ? "公共" : "我的"
}

export function optionLetter(index: number): string {
  return String.fromCharCode(65 + index)
}

export function questionStarter(questionId: string): string {
  return `我想从题库里的这道题开始（题目 ID: ${questionId}）。先让我说说思路。`
}

export function correctOptionText(question: QuestionDetail): string | null {
  if (!question.options || !question.correct_option) return null
  const index = question.correct_option.charCodeAt(0) - 65
  return question.options[index] ?? null
}

export function knowledgePointTitle(
  nodes: KnowledgePoint[],
  id: string | undefined,
): string | undefined {
  if (!id) return undefined
  return nodes.find((node) => node.id === id)?.title
}

export type KnowledgePointTreeNode = KnowledgePoint & {
  children: KnowledgePointTreeNode[]
}

/** 把后端返回的扁平目录还原成树；顺序沿用接口返回的教材顺序。 */
export function buildKnowledgePointTree(
  nodes: KnowledgePoint[],
): KnowledgePointTreeNode[] {
  const byId = new Map<string, KnowledgePointTreeNode>()
  for (const node of nodes) {
    byId.set(node.id, { ...node, children: [] })
  }

  const roots: KnowledgePointTreeNode[] = []
  for (const node of nodes) {
    const treeNode = byId.get(node.id)
    if (!treeNode) continue
    const parent = node.parent_id ? byId.get(node.parent_id) : undefined
    if (parent) {
      parent.children.push(treeNode)
    } else {
      roots.push(treeNode)
    }
  }
  return roots
}

/** 返回某节点所有祖先的 id，用于展开选中项所在的分支。 */
export function knowledgePointAncestors(
  nodes: KnowledgePoint[],
  id: string | undefined,
): string[] {
  if (!id) return []
  const parentById = new Map(nodes.map((node) => [node.id, node.parent_id]))
  const ancestors: string[] = []
  let current = parentById.get(id)
  while (current) {
    ancestors.push(current)
    current = parentById.get(current)
  }
  return ancestors
}

/**
 * 按当前 scope 的题量过滤树。
 * 选中节点即使变成 0 题也保留，避免筛选时树突然把用户甩回根节点。
 */
export function filterKnowledgePointTree(
  nodes: KnowledgePointTreeNode[],
  counts: Record<string, number>,
  options: { showEmpty: boolean; keepId?: string },
): KnowledgePointTreeNode[] {
  if (options.showEmpty) return nodes

  const result: KnowledgePointTreeNode[] = []
  for (const node of nodes) {
    const children = filterKnowledgePointTree(node.children, counts, options)
    if (
      (counts[node.id] ?? 0) > 0 ||
      node.id === options.keepId ||
      children.length > 0
    ) {
      result.push({ ...node, children })
    }
  }
  return result
}

const VALUE_ERROR_PREFIX = /^Value error,\s*/i

export function questionErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const message = error.message.replace(VALUE_ERROR_PREFIX, "").trim()
    if (message) return message
    if (error.status === 404) return "题目不存在，可能已被删除。"
    if (error.status === 403) return "公共题只读，不能修改。"
    if (error.status === 409) return "题目已有作答记录，不能删除。"
    if (error.status === 422) return "提交内容不符合要求，请检查后重试。"
    if (error.status >= 500) return "服务器暂时不可用，请稍后重试。"
    return fallback
  }
  if (error instanceof TypeError) return "无法连接服务器，请稍后重试。"
  if (error instanceof Error && error.message) return error.message
  return fallback
}

export function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

/* ------------------------------------------------------------------
   编辑器：受控状态 -> 后端 payload
   ------------------------------------------------------------------ */

export type QuestionEditorField =
  | "stem"
  | "options"
  | "correctOption"
  | "referenceAnswer"
  | "primaryKnowledgePointId"

export type QuestionEditorErrors = Partial<Record<QuestionEditorField, string>>

export type QuestionEditorDraft = {
  questionType: QuestionType
  stem: string
  optionTexts: string[]
  correctIndex: number
  referenceAnswer: string
  primaryKnowledgePointId: string
  secondaryKnowledgePointIds: string[]
}

export type QuestionDraftValidation = {
  errors: QuestionEditorErrors
  payload: QuestionInput | null
}

/**
 * 与后端 QuestionInput 的校验保持一致：
 * - 单选：2–6 个纯文本选项，正确答案必须是已填写项；
 * - 简答：options / correct_option 必须为 null，参考答案可选。
 */
export function validateQuestionDraft(
  draft: QuestionEditorDraft,
): QuestionDraftValidation {
  const errors: QuestionEditorErrors = {}
  const stem = draft.stem.trim()
  if (!stem) {
    errors.stem = "请填写题干。"
  } else if (stem.length > STEM_MAX_LENGTH) {
    errors.stem = `题干不能超过 ${STEM_MAX_LENGTH} 个字符。`
  }

  const primaryKnowledgePointId = draft.primaryKnowledgePointId.trim()
  if (!primaryKnowledgePointId) {
    errors.primaryKnowledgePointId = "请选择主知识点。"
  }

  const secondaryKnowledgePointIds = draft.secondaryKnowledgePointIds.filter(
    (id) => id && id !== primaryKnowledgePointId,
  )

  let payload: QuestionInput | null = null

  if (draft.questionType === "single_choice") {
    const filled = draft.optionTexts
      .map((text, index) => ({ text: text.trim(), index }))
      .filter((item) => item.text.length > 0)

    if (filled.length < MIN_OPTIONS) {
      errors.options = `单选题至少需要 ${MIN_OPTIONS} 个选项。`
    } else if (filled.length > MAX_OPTIONS) {
      errors.options = `单选题最多 ${MAX_OPTIONS} 个选项。`
    } else if (new Set(filled.map((item) => item.text)).size !== filled.length) {
      errors.options = "选项内容不能重复。"
    }

    const correctPosition = filled.findIndex(
      (item) => item.index === draft.correctIndex,
    )
    if (correctPosition < 0) {
      errors.correctOption = "正确答案必须指向一个已填写的选项。"
    }

    if (Object.keys(errors).length === 0) {
      payload = {
        question_type: "single_choice",
        stem,
        options: filled.map((item) => item.text),
        correct_option: LETTERS[correctPosition],
        reference_answer: null,
        primary_knowledge_point_id: primaryKnowledgePointId,
        secondary_knowledge_point_ids: secondaryKnowledgePointIds,
      }
    }
  } else {
    const referenceAnswer = draft.referenceAnswer.trim()
    if (referenceAnswer.length > REFERENCE_MAX_LENGTH) {
      errors.referenceAnswer = `参考答案不能超过 ${REFERENCE_MAX_LENGTH} 个字符。`
    }

    if (Object.keys(errors).length === 0) {
      payload = {
        question_type: "short_answer",
        stem,
        options: null,
        correct_option: null,
        reference_answer: referenceAnswer || null,
        primary_knowledge_point_id: primaryKnowledgePointId,
        secondary_knowledge_point_ids: secondaryKnowledgePointIds,
      }
    }
  }

  return { errors, payload }
}
