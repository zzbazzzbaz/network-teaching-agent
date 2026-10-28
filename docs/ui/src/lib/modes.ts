import type { AgentId, Mode } from "@/lib/mock"

export type PanelId = "questions" | "memory" | "sandbox"

export const MODES: Record<
  Mode,
  {
    id: Mode
    agentId: AgentId
    label: string
    path: string
    tagline: string
    description: string
    panels: { id: PanelId; label: string }[]
  }
> = {
  learn: {
    id: "learn",
    agentId: "teach_agent",
    label: "学习",
    path: "/learn",
    tagline: "对话、题库、记忆",
    description: "和苏格拉底式的老师对话，把概念问到能自己讲清楚。",
    panels: [
      { id: "questions", label: "题库" },
      { id: "memory", label: "记忆" },
    ],
  },
  lab: {
    id: "lab",
    agentId: "exp_agent",
    label: "实验",
    path: "/lab",
    tagline: "沙盒、终端、记忆",
    description: "在云端沙盒里跑命令、打开 VSCode，把协议拆开看。",
    panels: [
      { id: "sandbox", label: "沙盒" },
      { id: "memory", label: "记忆" },
    ],
  },
}
