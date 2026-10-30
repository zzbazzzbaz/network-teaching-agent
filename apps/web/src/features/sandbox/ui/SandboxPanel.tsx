import { useState } from "react"
import { toast } from "sonner"

import { cn } from "@/shared/lib/utils"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/shared/ui/alert-dialog"
import {
  WorkspaceHeader,
  workspaceContentClass,
} from "@/shared/ui/workspace-header"

import { sandboxErrorMessage } from "../model"
import {
  useDestroySandbox,
  usePauseSandbox,
  useSandbox,
  useStartSandbox,
} from "../queries"
import {
  AccountNote,
  SandboxDetails,
  SandboxError,
  SandboxIdle,
  SandboxLoading,
} from "./SandboxViews"
import { useSandboxHeartbeat } from "./useSandboxHeartbeat"

export function SandboxPanel() {
  const query = useSandbox()
  const start = useStartSandbox()
  const pause = usePauseSandbox()
  const destroy = useDestroySandbox()

  const [confirmDestroy, setConfirmDestroy] = useState(false)

  const sandbox = query.data ?? null
  const busy = start.isPending || pause.isPending || destroy.isPending

  useSandboxHeartbeat(sandbox)

  async function handleStart() {
    try {
      await start.mutateAsync()
      toast(sandbox?.status === "paused" ? "沙盒已恢复" : "沙盒已启动")
    } catch (error) {
      toast.error(sandboxErrorMessage(error, "启动沙盒失败"))
    }
  }

  async function handlePause() {
    try {
      await pause.mutateAsync()
      toast("沙盒已暂停")
    } catch (error) {
      toast.error(sandboxErrorMessage(error, "暂停沙盒失败"))
    }
  }

  async function handleDestroy() {
    try {
      const result = await destroy.mutateAsync()
      toast(result?.status === "stopping" ? "正在销毁沙盒" : "沙盒已销毁")
    } catch (error) {
      toast.error(sandboxErrorMessage(error, "销毁沙盒失败"))
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <WorkspaceHeader title="实验沙盒" />

      <div className="scroll-slim min-h-0 flex-1 overflow-y-auto">
        <div className={cn(workspaceContentClass, "py-5 lg:py-6")}>
          <div className="w-full">
            {query.isPending ? (
              <SandboxLoading />
            ) : query.isError && query.data === undefined ? (
              <SandboxError
                error={query.error}
                onRetry={() => void query.refetch()}
              />
            ) : sandbox ? (
              <SandboxDetails
                sandbox={sandbox}
                busy={busy}
                starting={start.isPending}
                pausing={pause.isPending}
                destroying={destroy.isPending}
                onStart={() => void handleStart()}
                onPause={() => void handlePause()}
                onDestroy={() => setConfirmDestroy(true)}
              />
            ) : (
              <SandboxIdle
                starting={start.isPending}
                onStart={() => void handleStart()}
              />
            )}

            <AccountNote />
          </div>
        </div>
      </div>

      <AlertDialog open={confirmDestroy} onOpenChange={setConfirmDestroy}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>销毁沙盒？</AlertDialogTitle>
            <AlertDialogDescription>
              所有实验会话共享这个 workspace。销毁后，其中的文件、代码和终端历史都无法恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmDestroy(false)
                void handleDestroy()
              }}
            >
              销毁沙盒
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
