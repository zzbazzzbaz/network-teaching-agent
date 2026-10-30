import { useSearch } from "@tanstack/react-router"

import { DraftRuntime } from "@/features/chat/model/DraftRuntime"
import { useDraftConversation } from "@/features/chat/model/useDraftConversation"
import { DraftFooter } from "@/features/chat/ui/DraftFooter"
import { MODES } from "@/features/sessions"
import { cn } from "@/shared/lib/utils"
import { workspaceContentClass } from "@/shared/ui/workspace-header"

import type { SessionSearch } from "./SessionPage"
import { WorkspaceBar } from "./WorkspaceBar"
import { WorkspacePanelPage } from "./WorkspacePanelPage"

const STEPS = [
  {
    id: "01",
    title: "说出你想观察的现象",
    body: "不用先写命令。想验证什么，就说什么。",
  },
  {
    id: "02",
    title: "先跑通最小的一步",
    body: "Agent 给一条能跑的命令，确认环境和输出。",
  },
  {
    id: "03",
    title: "把结果贴回来",
    body: "输出、报错、抓包都行，接着分析下一步。",
  },
]

export function LabHomePage() {
  const search = useSearch({ strict: false }) as SessionSearch
  const panel = MODES.lab.panels.find((item) => item.id === search.panel)?.id

  if (panel) {
    return <WorkspacePanelPage mode="lab" panel={panel} search={search} />
  }
  return <LabEntry />
}

function LabEntry() {
  const draft = useDraftConversation("lab")

  return (
    <DraftRuntime disabled={draft.starting} onNew={draft.startFromMessage}>
      <div className="flex h-dvh flex-col">
        <WorkspaceBar title="实验" />

        <div className="scroll-slim min-h-0 flex-1 overflow-y-auto">
          <div className={cn(workspaceContentClass, "py-6 lg:py-9")}>
            <header>
              <p className="font-mono text-[10px] tracking-[0.14em] text-ink-muted">
                COURSE LAB
              </p>
              <h1 className="mt-1.5 text-[21px] leading-tight font-semibold tracking-[-0.012em] text-ink">
                实验台
              </h1>
            </header>

            <ol className="mt-6 grid gap-2.5 sm:grid-cols-3">
              {STEPS.map((step) => (
                <li
                  key={step.id}
                  className="rounded-lg border border-line bg-surface p-3.5"
                >
                  <span className="font-mono text-[10px] tabular-nums text-ink-muted">
                    {step.id}
                  </span>
                  <p className="mt-1 text-[13.5px] font-medium text-ink">
                    {step.title}
                  </p>
                  <p className="mt-1 text-[11.5px] leading-5 text-ink-muted">
                    {step.body}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <DraftFooter
          mode="lab"
          starting={draft.starting}
          onStarter={(text) => void draft.start(text, [], "", "starter")}
        />
      </div>
    </DraftRuntime>
  )
}
