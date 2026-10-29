import { Plus, X } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import type { QuestionDetail, QuestionType } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select"
import { Textarea } from "@/shared/ui/textarea"

import {
  LETTERS,
  MAX_OPTIONS,
  MIN_OPTIONS,
  REFERENCE_MAX_LENGTH,
  STEM_MAX_LENGTH,
  knowledgePointIndent,
  optionBody,
  optionLetter,
  questionErrorMessage,
  validateQuestionDraft,
  type QuestionEditorDraft,
  type QuestionEditorErrors,
  type QuestionEditorField,
} from "../model"
import {
  useCreateQuestion,
  useKnowledgePoints,
  useUpdateQuestion,
} from "../queries"

const TYPE_CHOICES = [
  { id: "single_choice", label: "单选" },
  { id: "short_answer", label: "简答" },
] as const satisfies readonly { id: QuestionType; label: string }[]

const ERROR_FIELD_ORDER: readonly QuestionEditorField[] = [
  "stem",
  "options",
  "correctOption",
  "referenceAnswer",
  "primaryKnowledgePointId",
]

function fieldElementId(field: QuestionEditorField): string {
  switch (field) {
    case "stem":
      return "question-stem"
    case "options":
      return "question-option-0"
    case "correctOption":
      return "correct-option"
    case "referenceAnswer":
      return "reference-answer"
    case "primaryKnowledgePointId":
      return "question-primary-kp"
  }
}

export function QuestionEditorDialog({
  question,
  defaultKnowledgePointId,
  onClose,
  onSaved,
}: {
  question: QuestionDetail | null
  defaultKnowledgePointId?: string
  onClose: () => void
  onSaved: (questionId: string, created: boolean) => void
}) {
  const [questionType, setQuestionType] = useState<QuestionType>(
    question?.question_type ?? "single_choice",
  )
  const [stem, setStem] = useState(question?.stem ?? "")
  const [optionTexts, setOptionTexts] = useState<string[]>(() =>
    question?.question_type === "single_choice" && question.options?.length
      ? question.options.map(optionBody)
      : ["", "", "", ""],
  )
  const [correctIndex, setCorrectIndex] = useState(() => {
    if (!question?.options || !question.correct_option) return 0
    const index = question.options.findIndex(
      (option) => optionLetter(option) === question.correct_option,
    )
    return index >= 0 ? index : 0
  })
  const [referenceAnswer, setReferenceAnswer] = useState(
    question?.question_type === "short_answer"
      ? (question.reference_answer ?? "")
      : "",
  )
  const [primaryKnowledgePointId, setPrimaryKnowledgePointId] = useState(
    question?.primary_knowledge_point.id ?? defaultKnowledgePointId ?? "",
  )
  const [errors, setErrors] = useState<QuestionEditorErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)

  const knowledgePointsQuery = useKnowledgePoints()
  const createQuestion = useCreateQuestion()
  const updateQuestion = useUpdateQuestion()
  const pending = createQuestion.isPending || updateQuestion.isPending
  const nodes = knowledgePointsQuery.data?.nodes ?? []
  const secondaryKnowledgePointIds =
    question?.secondary_knowledge_points.map((point) => point.id) ?? []

  function clearError(field: QuestionEditorField) {
    setSubmitError(null)
    setErrors((previous) => {
      if (!previous[field]) return previous
      const next = { ...previous }
      delete next[field]
      return next
    })
  }

  function changeType(next: QuestionType) {
    setQuestionType(next)
    setErrors({})
    setSubmitError(null)
  }

  function changeOption(index: number, value: string) {
    setOptionTexts((previous) =>
      previous.map((text, itemIndex) =>
        itemIndex === index ? value : text,
      ),
    )
    clearError("options")
    clearError("correctOption")
  }

  function addOption() {
    if (optionTexts.length >= MAX_OPTIONS) return
    setOptionTexts((previous) => [...previous, ""])
    clearError("options")
  }

  function removeOption(index: number) {
    if (optionTexts.length <= MIN_OPTIONS) return
    setOptionTexts((previous) =>
      previous.filter((_, itemIndex) => itemIndex !== index),
    )
    setCorrectIndex((previous) => {
      if (previous === index) return 0
      if (previous > index) return previous - 1
      return previous
    })
    clearError("options")
    clearError("correctOption")
  }

  function selectCorrectOption(letter: string) {
    const index = LETTERS.findIndex((item) => item === letter)
    if (index < 0) return
    setCorrectIndex(index)
    clearError("correctOption")
  }

  async function submit() {
    if (pending) return
    setSubmitError(null)

    const draft: QuestionEditorDraft = {
      questionType,
      stem,
      optionTexts,
      correctIndex,
      referenceAnswer,
      primaryKnowledgePointId,
      secondaryKnowledgePointIds,
    }
    const { payload, errors: nextErrors } = validateQuestionDraft(draft)
    setErrors(nextErrors)
    if (!payload) {
      const firstInvalid = ERROR_FIELD_ORDER.find(
        (field) => nextErrors[field],
      )
      if (firstInvalid) {
        window.setTimeout(() => {
          document.getElementById(fieldElementId(firstInvalid))?.focus()
        }, 0)
      }
      return
    }

    try {
      if (question) {
        await updateQuestion.mutateAsync({
          questionId: question.question_id,
          input: payload,
        })
        toast("题目已更新")
        onSaved(question.question_id, false)
      } else {
        const created = await createQuestion.mutateAsync(payload)
        toast("已保存到我的题库")
        onSaved(created.question_id, true)
      }
    } catch (error) {
      setSubmitError(
        questionErrorMessage(
          error,
          question ? "保存失败，请稍后重试。" : "创建失败，请稍后重试。",
        ),
      )
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !pending) onClose()
      }}
    >
      <DialogContent className="max-w-xl gap-5">
        <DialogHeader>
          <DialogTitle>{question ? "编辑私有题" : "新建私有题"}</DialogTitle>
          <DialogDescription>
            {question
              ? "修改只会影响「我的题库」，公共题库保持不变。"
              : "只会保存到「我的题库」，不会修改公共题库。"}
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
              {TYPE_CHOICES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={questionType === item.id}
                  onClick={() => changeType(item.id)}
                  className={cn(
                    "h-9 rounded-sm border text-[12.5px] font-medium transition-colors sm:h-8",
                    questionType === item.id
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
              onChange={(event) => {
                setStem(event.target.value)
                clearError("stem")
              }}
              rows={3}
              maxLength={STEM_MAX_LENGTH}
              placeholder="用一句话描述问题…"
              autoComplete="off"
              aria-invalid={Boolean(errors.stem)}
              aria-describedby={errors.stem ? "question-stem-error" : undefined}
              className="min-h-24 text-[16px] sm:text-[14px]"
            />
            {errors.stem && (
              <p
                id="question-stem-error"
                role="alert"
                className="text-[12px] text-danger"
              >
                {errors.stem}
              </p>
            )}
          </div>

          {questionType === "single_choice" && (
            <>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <Label>选项</Label>
                  <span className="text-[10.5px] text-ink-muted">
                    字母会自动添加
                  </span>
                </div>
                <div className="space-y-2">
                  {optionTexts.map((option, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="w-4 shrink-0 font-mono text-[11px] text-ink-muted">
                        {LETTERS[index]}
                      </span>
                      <Input
                        id={`question-option-${index}`}
                        value={option}
                        onChange={(event) =>
                          changeOption(index, event.target.value)
                        }
                        placeholder={`选项 ${LETTERS[index]}`}
                        aria-label={`选项 ${LETTERS[index]}`}
                        aria-invalid={Boolean(errors.options)}
                        aria-describedby={
                          errors.options ? "question-options-error" : undefined
                        }
                        name={`option-${index}`}
                        autoComplete="off"
                        spellCheck={false}
                        className="h-10 text-[16px] sm:h-9 sm:text-[14px]"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`删除选项 ${LETTERS[index]}`}
                        disabled={optionTexts.length <= MIN_OPTIONS}
                        onClick={() => removeOption(index)}
                      >
                        <X className="size-3.5" aria-hidden="true" />
                      </Button>
                    </div>
                  ))}
                </div>
                {optionTexts.length < MAX_OPTIONS && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1 px-1 text-[12px]"
                    onClick={addOption}
                  >
                    <Plus className="size-3.5" aria-hidden="true" />
                    添加选项
                  </Button>
                )}
                {errors.options && (
                  <p
                    id="question-options-error"
                    role="alert"
                    className="text-[12px] text-danger"
                  >
                    {errors.options}
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="correct-option">正确答案</Label>
                <Select
                  value={LETTERS[correctIndex]}
                  onValueChange={selectCorrectOption}
                >
                  <SelectTrigger
                    id="correct-option"
                    aria-describedby={
                      errors.correctOption
                        ? "question-correct-option-error"
                        : undefined
                    }
                    className="w-28"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {optionTexts.map((_, index) => (
                      <SelectItem key={LETTERS[index]} value={LETTERS[index]}>
                        {LETTERS[index]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.correctOption && (
                  <p
                    id="question-correct-option-error"
                    role="alert"
                    className="text-[12px] text-danger"
                  >
                    {errors.correctOption}
                  </p>
                )}
              </div>
            </>
          )}

          {questionType === "short_answer" && (
            <div className="space-y-1.5">
              <Label htmlFor="reference-answer">参考答案</Label>
              <Textarea
                id="reference-answer"
                name="reference-answer"
                value={referenceAnswer}
                onChange={(event) => {
                  setReferenceAnswer(event.target.value)
                  clearError("referenceAnswer")
                }}
                rows={4}
                maxLength={REFERENCE_MAX_LENGTH}
                placeholder="可以留空，之后在对话里补充。"
                autoComplete="off"
                aria-invalid={Boolean(errors.referenceAnswer)}
                aria-describedby={
                  errors.referenceAnswer ? "reference-answer-error" : undefined
                }
                className="text-[16px] sm:text-[14px]"
              />
              {errors.referenceAnswer && (
                <p
                  id="reference-answer-error"
                  role="alert"
                  className="text-[12px] text-danger"
                >
                  {errors.referenceAnswer}
                </p>
              )}
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="question-primary-kp">主知识点</Label>
            <Select
              value={primaryKnowledgePointId}
              onValueChange={(value) => {
                setPrimaryKnowledgePointId(value)
                clearError("primaryKnowledgePointId")
              }}
              disabled={
                knowledgePointsQuery.isPending || knowledgePointsQuery.isError
              }
            >
              <SelectTrigger
                id="question-primary-kp"
                aria-describedby={
                  errors.primaryKnowledgePointId
                    ? "question-primary-kp-error"
                    : undefined
                }
                className="h-10 w-full sm:h-9"
              >
                <SelectValue
                  placeholder={
                    knowledgePointsQuery.isPending
                      ? "正在加载知识点…"
                      : "选择主知识点"
                  }
                  className="min-w-0 truncate"
                />
              </SelectTrigger>
              <SelectContent className="max-h-64">
                {nodes.map((node) => (
                  <SelectItem key={node.id} value={node.id}>
                    {knowledgePointIndent(node.level)}
                    {node.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {knowledgePointsQuery.isError && (
              <p role="alert" className="text-[12px] text-danger">
                知识点目录加载失败，请关闭后重试。
              </p>
            )}
            {errors.primaryKnowledgePointId && (
              <p
                id="question-primary-kp-error"
                role="alert"
                className="text-[12px] text-danger"
              >
                {errors.primaryKnowledgePointId}
              </p>
            )}
          </div>

          {submitError && (
            <p
              role="alert"
              className="rounded-md border border-danger-line bg-danger-soft px-3 py-2 text-[12px] leading-5 text-danger"
            >
              {submitError}
            </p>
          )}
        </div>

        <DialogFooter className="sticky bottom-0 -mx-5 -mb-5 mt-1 border-t border-line bg-surface px-5 py-3">
          <Button
            type="button"
            variant="outline"
            className="h-11 sm:h-9"
            disabled={pending}
            onClick={onClose}
          >
            取消
          </Button>
          <Button
            type="button"
            className="h-11 sm:h-9"
            disabled={pending}
            onClick={() => void submit()}
          >
            {pending ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
