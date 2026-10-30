import type { AgentId, Mode, Session } from "@/shared/api/types"

export const DEFAULT_SESSION_TITLE = "新会话"

export const MODES = {
  learn: {
    id: "learn",
    agentId: "teach_agent",
    label: "学习",
    path: "/learn",
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
    panels: readonly { id: PanelId; label: string }[]
  }
>

export type PanelId = "questions" | "memory" | "sandbox"

/** 工作区 URL 的 search 形状，题库/记忆/沙盒共用。 */
export type SessionSearch = {
  panel?: PanelId
  question?: string
  kp?: string
  path?: string
}

export function modeForAgent(agentId: AgentId): Mode {
  return agentId === "teach_agent" ? "learn" : "lab"
}

export function isSessionForMode(session: Session, mode: Mode): boolean {
  return session.agent_id === MODES[mode].agentId
}

export function panelLabel(mode: Mode, panel: PanelId | undefined): string | null {
  if (!panel) return null
  return MODES[mode].panels.find((item) => item.id === panel)?.label ?? null
}
