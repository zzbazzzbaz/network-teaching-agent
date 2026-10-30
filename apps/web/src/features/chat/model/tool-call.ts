/** 工具卡片的纯数据解析与展示辅助，不依赖 React。 */

export function pretty(value: unknown): string {
  if (value === undefined || value === null) return ""
  if (typeof value === "string") return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function truncate(value: string, max = 12_000): string {
  return value.length > max ? `${value.slice(0, max)}\n…（已截断）` : value
}

export function argString(
  args: unknown,
  keys: string[],
): string | undefined {
  if (!args || typeof args !== "object") return undefined
  const record = args as Record<string, unknown>
  for (const key of keys) {
    if (typeof record[key] === "string" && record[key]) return record[key]
  }
  return undefined
}

export function summaryFor(toolName: string, args: unknown): string {
  if (toolName === "execute") {
    return argString(args, ["command", "cmd"]) ?? "执行命令"
  }
  if (toolName.includes("search")) return "检索题库"
  if (toolName.includes("save")) return "保存到我的题库"
  if (toolName === "import_questions") return "导入题目"
  if (toolName.includes("sandbox")) return "确认实验沙盒"
  if (toolName === "task") return "分派子任务"
  if (toolName.includes("read")) {
    return argString(args, ["path", "file_path"]) ?? "读取文件"
  }
  if (toolName.includes("write")) {
    return argString(args, ["path", "file_path"]) ?? "写入文件"
  }
  return "工具调用"
}

export function statusLabel(
  status: { type: string },
  isError?: boolean,
): string {
  if (isError) return "失败"
  if (status.type === "running") return "运行中"
  if (status.type === "complete") return "完成"
  if (status.type === "requires-action") return "等待作答"
  return "未完成"
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined
}

function asText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined
}

export type AskQuestionData = {
  mode?: "single_choice" | "short_answer"
  question?: string
  options: string[]
  correctOption?: string
  referenceAnswer?: string
}

/** ask_student 的参数既有早期的扁平结构，也有现在嵌套的 question 对象。 */
export function parseAskQuestion(args: unknown): AskQuestionData {
  const root = asRecord(args) ?? {}
  const nested = asRecord(root.question)
  const source = nested ?? root
  const rawMode = asText(source.mode) ?? asText(root.mode)
  const optionsValue = Array.isArray(source.options)
    ? source.options
    : Array.isArray(root.options)
      ? root.options
      : []

  return {
    mode:
      rawMode === "single_choice" || rawMode === "short_answer"
        ? rawMode
        : undefined,
    question:
      asText(source.stem) ??
      asText(source.question) ??
      asText(root.question),
    options: optionsValue.filter(
      (value): value is string => typeof value === "string",
    ),
    correctOption: asText(source.correct_option)?.toUpperCase(),
    referenceAnswer: asText(source.reference_answer),
  }
}

export function parseAskResult(value: unknown): {
  student?: string
  reference?: string
} {
  const text = pretty(value)
  return {
    student:
      /学生答案[：:]\s*([\s\S]*?)(?=\n参考答案[：:]|\n（题库记录失败|$)/.exec(
        text,
      )?.[1]?.trim(),
    reference:
      /参考答案[：:]\s*([\s\S]*?)(?=\n（题库记录失败|$)/.exec(text)?.[1]?.trim(),
  }
}

export function optionLabel(
  letter: string | undefined,
  options: string[],
): string | undefined {
  if (!letter) return undefined
  const index = letter.charCodeAt(0) - 65
  if (index < 0 || index >= options.length) return letter
  const option = options[index].trim()
  return new RegExp(`^${letter}[.、\\s]`, "i").test(option)
    ? option
    : `${letter}. ${option}`
}
