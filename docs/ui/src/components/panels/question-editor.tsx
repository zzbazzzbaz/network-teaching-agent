import { Plus, X } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { knowledgePoints, type Question } from "@/lib/mock"
import { useStore } from "@/lib/store"
import { cn } from "@/lib/utils"

const LETTERS = ["A", "B", "C", "D", "E", "F"]
const DEFAULT_KP = "5.8.2"

const uid = () => Math.random().toString(36).slice(2, 9)

export function QuestionEditor({
  open,
  question,
  onOpenChange,
}: {
  open: boolean
  question: Question | null
  onOpenChange: (open: boolean) => void
}) {
  const { addQuestion, updateQuestion } = useStore()
  const [type, setType] = useState<Question["type"]>("single_choice")
  const [stem, setStem] = useState("")
  const [options, setOptions] = useState(["", "", "", ""])
  const [correct, setCorrect] = useState("A")
  const [reference, setReference] = useState("")
  const [kp, setKp] = useState(DEFAULT_KP)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!open) return
    setError("")
    if (question) {
      setType(question.type)
      setStem(question.stem)
      setOptions(
        question.options
          ? question.options.map((option) =>
              option.replace(/^[A-F][.、]\s*/, ""),
            )
          : ["", "", "", ""],
      )
      setCorrect(question.correctOption ?? "A")
      setReference(question.referenceAnswer ?? "")
      setKp(question.kpId)
    } else {
      setType("single_choice")
      setStem("")
      setOptions(["", "", "", ""])
      setCorrect("A")
      setReference("")
      setKp(DEFAULT_KP)
    }
  }, [open, question])

  function save() {
    const stemText = stem.trim()
    const cleanOptions = options.map((option) => option.trim())

    if (!stemText) {
      setError("请填写题干。")
      return
    }
    if (!kp) {
      setError("请选择主知识点。")
      return
    }
    if (type === "single_choice") {
      const filled = cleanOptions.filter(Boolean)
      if (filled.length < 2) {
        setError("单选题至少需要两个选项。")
        return
      }
      const correctIndex = LETTERS.indexOf(correct)
      if (correctIndex < 0 || !cleanOptions[correctIndex]) {
        setError("正确答案必须指向一个已填写的选项。")
        return
      }
    }

    const payload: Question = {
      id: question?.id ?? `q-local-${uid()}`,
      origin: "mine",
      type,
      stem: stemText,
      options: undefined,
      correctOption: undefined,
      referenceAnswer:
        type === "short_answer" ? reference.trim() || undefined : undefined,
      kpId: kp,
      lastAttemptAt: question?.lastAttemptAt,
    }

    if (type === "single_choice") {
      const filled = options
        .map((text, index) => ({ text: text.trim(), index }))
        .filter((item) => item.text)
      const correctIndex = LETTERS.indexOf(correct)
      const correctPosition = filled.findIndex((item) => item.index === correctIndex)
      if (correctPosition < 0) {
        setError("正确答案必须指向一个已填写的选项。")
        return
      }
      payload.options = filled.map(
        (item, index) => `${LETTERS[index]}. ${item.text}`,
      )
      payload.correctOption = LETTERS[correctPosition]
    }

    if (question) {
      updateQuestion(payload)
      toast("题目已更新")
    } else {
      addQuestion(payload)
      toast("已保存到我的题库")
    }
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl gap-5">
        <DialogHeader>
          <DialogTitle>{question ? "编辑私有题" : "新建私有题"}</DialogTitle>
          <DialogDescription>
            只会保存到「我的题库」，不会修改公共题库。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>题型</Label>
            <div
              role="group"
              aria-label="题型"
              className="grid grid-cols-2 gap-0.5 rounded-md bg-surface-3 p-0.5"
            >
              {(
                [
                  { id: "single_choice", label: "单选" },
                  { id: "short_answer", label: "简答" },
                ] as const
              ).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={type === item.id}
                  onClick={() => setType(item.id)}
                  className={cn(
                    "h-8 rounded-sm border text-[12.5px] font-medium transition-colors",
                    type === item.id
                      ? "border-line bg-surface text-ink"
                      : "border-transparent text-ink-muted hover:text-ink",
                  )}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="question-stem">题干</Label>
            <Textarea
              id="question-stem"
              name="stem"
              value={stem}
              onChange={(event) => setStem(event.target.value)}
              rows={3}
              placeholder="用一句话描述问题…"
              autoComplete="off"
              className="min-h-24 text-[16px] lg:text-[14px]"
            />
          </div>

          {type === "single_choice" && (
            <>
              <div className="space-y-1.5">
                <Label>选项</Label>
                <div className="space-y-2">
                  {options.map((option, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="w-4 shrink-0 font-mono text-[11px] text-ink-muted">
                        {LETTERS[index]}
                      </span>
                      <Input
                        value={option}
                        onChange={(event) =>
                          setOptions((prev) =>
                            prev.map((item, itemIndex) =>
                              itemIndex === index ? event.target.value : item,
                            ),
                          )
                        }
                        placeholder={`选项 ${LETTERS[index]}`}
                        aria-label={`选项 ${LETTERS[index]}`}
                        name={`option-${index}`}
                        autoComplete="off"
                        spellCheck={false}
                        className="text-[16px] lg:text-[14px]"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`删除选项 ${LETTERS[index]}`}
                        disabled={options.length <= 2}
                        onClick={() =>
                          setOptions((prev) =>
                            prev.filter((_, itemIndex) => itemIndex !== index),
                          )
                        }
                      >
                        <X className="size-3.5" aria-hidden="true" />
                      </Button>
                    </div>
                  ))}
                </div>
                {options.length < LETTERS.length && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1 px-1 text-[12px]"
                    onClick={() => setOptions((prev) => [...prev, ""])}
                  >
                    <Plus className="size-3.5" aria-hidden="true" />
                    添加选项
                  </Button>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="correct-option">正确答案</Label>
                <Select value={correct} onValueChange={setCorrect}>
                  <SelectTrigger id="correct-option" className="w-28">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {options.map((_, index) => (
                      <SelectItem key={LETTERS[index]} value={LETTERS[index]}>
                        {LETTERS[index]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {type === "short_answer" && (
            <div className="space-y-1.5">
              <Label htmlFor="reference-answer">参考答案</Label>
              <Textarea
                id="reference-answer"
                name="reference-answer"
                value={reference}
                onChange={(event) => setReference(event.target.value)}
                rows={4}
                placeholder="可以留空，之后在对话里补充。"
                autoComplete="off"
                className="text-[16px] lg:text-[14px]"
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="knowledge-point">主知识点</Label>
            <Select value={kp} onValueChange={setKp}>
              <SelectTrigger id="knowledge-point" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-64">
                {knowledgePoints.map((point) => (
                  <SelectItem key={point.id} value={point.id}>
                    {"\u00A0".repeat(Math.max(0, point.level - 1) * 2)}
                    {point.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && (
            <p role="alert" className="text-[12px] text-danger">
              {error}
            </p>
          )}
        </div>

        <DialogFooter className="sticky bottom-0 -mx-5 -mb-5 mt-1 border-t border-line bg-surface px-5 py-3">
          <Button variant="outline" className="h-11 sm:h-9" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button className="h-11 sm:h-9" onClick={save}>保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
