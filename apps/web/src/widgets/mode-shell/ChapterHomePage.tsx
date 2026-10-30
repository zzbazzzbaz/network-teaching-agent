import { ArrowUpRight, ChevronDown } from "lucide-react"
import { useState } from "react"
import { useSearch } from "@tanstack/react-router"

import { DraftRuntime } from "@/features/chat/model/DraftRuntime"
import { useDraftConversation } from "@/features/chat/model/useDraftConversation"
import { DraftFooter } from "@/features/chat/ui/DraftFooter"
import {
  sessionTitleFor,
  starterPromptFor,
  useCourseOutline,
  type CourseChapter,
  type CourseTarget,
} from "@/features/course"
import { MODES } from "@/features/sessions"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import { workspaceContentClass } from "@/shared/ui/workspace-header"

import type { SessionSearch } from "./SessionPage"
import { WorkspaceBar } from "./WorkspaceBar"
import { WorkspacePanelPage } from "./WorkspacePanelPage"

function ChapterCard({
  chapter,
  startingId,
  onStart,
}: {
  chapter: CourseChapter
  startingId: string | null
  onStart: (target: CourseTarget) => void
}) {
  const [open, setOpen] = useState(false)
  const busy = startingId === chapter.id
  const disabled = startingId !== null

  return (
    <li className="flex flex-col overflow-hidden rounded-lg border border-line bg-surface">
      <button
        type="button"
        onClick={() =>
          onStart({ kind: "chapter", id: chapter.id, title: chapter.title })
        }
        disabled={disabled}
        className="group flex flex-1 items-start gap-2.5 p-3.5 text-left transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:bg-surface"
      >
        <span className="mt-0.5 font-mono text-[10px] tabular-nums text-ink-muted">
          {chapter.id.padStart(2, "0")}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13.5px] font-medium text-ink">
            {chapter.title}
          </span>
        </span>
        {busy ? (
          <span
            aria-label="正在创建"
            className="mt-1 size-3 animate-spin rounded-full border-2 border-line-strong border-t-link"
          />
        ) : (
          <ArrowUpRight
            className="mt-1 size-3.5 shrink-0 text-ink-muted transition-colors group-hover:text-link"
            aria-hidden="true"
          />
        )}
      </button>

      {chapter.sections.length > 0 && (
        <div className="border-t border-line">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="flex w-full items-center justify-between px-3.5 py-1.5 text-[11px] text-ink-muted transition-colors hover:text-ink"
          >
            从某一节开始
            <ChevronDown
              className={cn(
                "size-3.5 transition-transform",
                open && "rotate-180",
              )}
              aria-hidden="true"
            />
          </button>

          {open && (
            <ul className="px-1.5 pb-1.5">
              {chapter.sections.map((section) => (
                <li key={section.id}>
                  <button
                    type="button"
                    onClick={() =>
                      onStart({
                        kind: "section",
                        id: section.id,
                        title: section.title,
                        chapterTitle: chapter.title,
                      })
                    }
                    disabled={disabled}
                    className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-[12px] text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:bg-transparent"
                  >
                    <span className="w-10 shrink-0 font-mono text-[10px] tabular-nums text-ink-muted">
                      {section.id}
                    </span>
                    <span className="truncate">{section.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  )
}

export function ChapterHomePage() {
  const search = useSearch({ strict: false }) as SessionSearch
  const panel = MODES.learn.panels.find((item) => item.id === search.panel)?.id

  if (panel) {
    return <WorkspacePanelPage mode="learn" panel={panel} search={search} />
  }
  return <ChapterEntry />
}

function ChapterEntry() {
  const outlineQuery = useCourseOutline()
  const draft = useDraftConversation("learn")

  function startChapter(target: CourseTarget) {
    void draft.start(
      starterPromptFor(target),
      [],
      sessionTitleFor(target),
      target.id,
    )
  }

  const chapters = outlineQuery.outline

  return (
    <DraftRuntime disabled={draft.starting} onNew={draft.startFromMessage}>
      <div className="flex h-dvh flex-col">
        <WorkspaceBar title="学习" />

        <div className="scroll-slim min-h-0 flex-1 overflow-y-auto">
          <div className={cn(workspaceContentClass, "py-6 lg:py-9")}>
            <header>
              <p className="font-mono text-[10px] tracking-[0.14em] text-ink-muted">
                COURSE MAP
              </p>
              <h1 className="mt-1.5 text-[21px] leading-tight font-semibold tracking-[-0.012em] text-ink">
                从章节开始学习
              </h1>
            </header>

            {outlineQuery.isLoading ? (
              <div
                className="mt-5 grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3"
                aria-label="章节加载中"
              >
                {Array.from({ length: 9 }, (_, index) => (
                  <div
                    key={index}
                    className="h-[92px] animate-pulse rounded-lg bg-surface-3"
                  />
                ))}
              </div>
            ) : outlineQuery.isError ? (
              <div className="mt-5 rounded-lg border border-line bg-surface px-4 py-8 text-center">
                <p className="text-[13px] font-medium text-ink">
                  章节暂时打不开
                </p>
                <p className="mt-1.5 text-[12px] leading-6 text-ink-muted">
                  {outlineQuery.error instanceof Error
                    ? outlineQuery.error.message
                    : "请稍后重试。"}
                </p>
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => void outlineQuery.refetch()}
                >
                  重试
                </Button>
              </div>
            ) : chapters.length === 0 ? (
              <div className="mt-5 rounded-lg border border-line bg-surface px-4 py-8 text-center">
                <p className="text-[13px] font-medium text-ink">
                  还没有章节数据
                </p>
                <p className="mt-1.5 text-[12px] leading-6 text-ink-muted">
                  教材目录为空，请先检查课程资源。
                </p>
              </div>
            ) : (
              <ul
                className="mt-5 grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3"
                aria-label="章节列表"
              >
                {chapters.map((chapter) => (
                  <ChapterCard
                    key={chapter.id}
                    chapter={chapter}
                    startingId={draft.startingId}
                    onStart={startChapter}
                  />
                ))}
              </ul>
            )}
          </div>
        </div>

        <DraftFooter
          mode="learn"
          starting={draft.starting}
          onStarter={(text) => void draft.start(text, [], "", "starter")}
        />
      </div>
    </DraftRuntime>
  )
}
