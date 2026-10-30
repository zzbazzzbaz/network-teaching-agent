import { toast } from "sonner"

import { humanizeApiError } from "@/shared/api/errors"
import type { Session } from "@/shared/api/types"
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
import { DEFAULT_SESSION_TITLE, useDeleteSession } from "@/features/sessions"

export function DeleteSessionDialog({
  session,
  onClose,
  onDeleted,
}: {
  session: Session | null
  onClose: () => void
  onDeleted: (session: Session) => void
}) {
  const remove = useDeleteSession()

  async function confirm() {
    if (!session) return
    try {
      await remove.mutateAsync(session)
      toast("会话已删除")
      onClose()
      onDeleted(session)
    } catch (error) {
      toast.error(humanizeApiError(error, "删除会话失败"))
    }
  }

  return (
    <AlertDialog
      open={Boolean(session)}
      onOpenChange={(open) => {
        if (!open && !remove.isPending) onClose()
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>删除这个会话？</AlertDialogTitle>
          <AlertDialogDescription>
            「{session?.title || DEFAULT_SESSION_TITLE}」的对话记录会被删除。题库中的题目和沙盒里的文件不受影响。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={remove.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={(event) => {
              event.preventDefault()
              void confirm()
            }}
            disabled={remove.isPending}
          >
            {remove.isPending ? "删除中…" : "删除"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
