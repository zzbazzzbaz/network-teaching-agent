import type { KnowledgePoint } from "@/shared/api/types"

/**
 * 教材目录 -> 章节入口用的两级结构。
 * 章是入口，节只用来定位起点；子节不在这里展开。
 */
export type CourseSection = {
  id: string
  title: string
}

export type CourseChapter = {
  id: string
  title: string
  sections: CourseSection[]
}

export type CourseTarget =
  | { kind: "chapter"; id: string; title: string }
  | { kind: "section"; id: string; title: string; chapterTitle: string }

function compareIds(a: string, b: string): number {
  const left = a.split(".").map(Number)
  const right = b.split(".").map(Number)
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const delta = (left[index] ?? 0) - (right[index] ?? 0)
    if (delta !== 0) return delta
  }
  return a.localeCompare(b)
}

function isChapterNode(node: KnowledgePoint): boolean {
  // level 0 的 `99` 是跨章节综合节点，不是章。
  return (
    node.parent_id === null &&
    /^\d{1,2}$/.test(node.id) &&
    Number(node.id) < 90
  )
}

export function buildCourseOutline(
  nodes: KnowledgePoint[],
): CourseChapter[] {
  const chapterNodes = nodes.filter(isChapterNode).sort(
    (a, b) => compareIds(a.id, b.id),
  )

  return chapterNodes.map((chapter) => ({
    id: chapter.id,
    title: chapter.title,
    sections: nodes
      .filter(
        (node) => node.level === 2 && node.parent_id === chapter.id,
      )
      .sort((a, b) => compareIds(a.id, b.id))
      .map((node) => ({ id: node.id, title: node.title })),
  }))
}

export function sessionTitleFor(target: CourseTarget): string {
  if (target.kind === "chapter") {
    return `第${target.id}章 ${target.title}`
  }
  return `${target.id} ${target.title}`
}

export function starterPromptFor(target: CourseTarget): string {
  if (target.kind === "chapter") {
    return `我想从第 ${target.id} 章「${target.title}」开始，先给我这一章的地图，再出两道诊断题，最后告诉我从哪一节开始。`
  }
  return `我想从 ${target.id}「${target.title}」开始，先告诉我这一节要讲什么，再出两道诊断题。`
}
