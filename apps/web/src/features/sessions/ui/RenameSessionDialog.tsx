import { useEffect, useState } from "react"
import { toast } from "sonner"

import { humanizeApiError } from "@/shared/api/errors"
import type { Session } from "@/shared/api/types"
import { Button } from "@/shared/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { DEFAULT_SESSION_TITLE, useRenameSession } from "@/features/sessions"

export function RenameSessionDialog({
  session,
  onClose,
}: {
  session: Session | null
  onClose: () => void
}) {
  const rename = useRenameSession()
  const [draftTitle, setDraftTitle] = useState("")

  useEffect(() => {
    if (session) setDraftTitle(session.title || DEFAULT_SESSION_TITLE)
  }, [session])

  async function save() {
    if (!session) return
    const title = draftTitle.trim() || DEFAULT_SESSION_TITLE
    if (title === session.title) {
      onClose()
      return
    }
    try {
      await rename.mutateAsync({ sessionId: session.session_id, title })
      toast("会话已重命名")
      onClose()
    } catch (error) {
      toast.error(humanizeApiError(error, "重命名失败"))
    }
  }

  return (
    <Dialog
      open={Boolean(session)}
      onOpenChange={(open) => {
        if (!open && !rename.isPending) onClose()
      }}
    >
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>重命名会话</DialogTitle>
          <DialogDescription className="sr-only">
            修改这个会话在侧栏里的标题。
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            void save()
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="session-title">会话标题</Label>
            <Input
              id="session-title"
              name="session-title"
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              maxLength={100}
              autoComplete="off"
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={rename.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={rename.isPending}>
              {rename.isPending ? "保存中…" : "保存"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
