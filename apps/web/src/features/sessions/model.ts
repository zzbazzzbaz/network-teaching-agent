import type { AgentId, Mode, Session } from "@/shared/api/types"

export const DEFAULT_SESSION_TITLE = "新会话"

export const MODES = {
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
} as const satisfies Record<
  Mode,
  {
    id: Mode
    agentId: AgentId
    label: string
    path: string
    tagline: string
    description: string
    panels: readonly { id: PanelId; label: string }[]
  }
>

export type PanelId = "questions" | "memory" | "sandbox"

export function modeForAgent(agentId: AgentId): Mode {
  return agentId === "teach_agent" ? "learn" : "lab"
}

export function agentForMode(mode: Mode): AgentId {
  return MODES[mode].agentId
}

export function modeFromPath(pathname: string): Mode {
  return pathname.startsWith("/lab") ? "lab" : "learn"
}

export function isSessionForMode(session: Session, mode: Mode): boolean {
  return session.agent_id === MODES[mode].agentId
}

export function panelLabel(mode: Mode, panel: PanelId | undefined): string | null {
  if (!panel) return null
  return MODES[mode].panels.find((item) => item.id === panel)?.label ?? null
}
