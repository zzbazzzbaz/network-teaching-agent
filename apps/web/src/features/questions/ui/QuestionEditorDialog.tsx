import { useState } from "react"
import { toast } from "sonner"

import { useKnowledgePoints } from "@/features/course"
import type {
  QuestionDetail,
  QuestionInput,
  QuestionType,
} from "@/shared/api/types"
import { Button } from "@/shared/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog"

import {
  LETTERS,
  MAX_OPTIONS,
  MIN_OPTIONS,
  questionErrorMessage,
  validateQuestionDraft,
  type QuestionEditorDraft,
  type QuestionEditorErrors,
  type QuestionEditorField,
} from "../model"
import {
  useCreateQuestion,
  useUpdateQuestion,
} from "../queries"
import {
  QuestionKnowledgePointField,
  QuestionOptionsField,
  QuestionReferenceField,
  QuestionStemField,
  QuestionTypeField,
} from "./QuestionFormFields"

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
  onSubmit,
  initialCorrectOption,
}: {
  question: QuestionDetail | null
  defaultKnowledgePointId?: string
  onClose: () => void
  onSaved?: (questionId: string, created: boolean) => void
  onSubmit?: (input: QuestionInput) => Promise<void> | void
  initialCorrectOption?: string | null
}) {
  const [questionType, setQuestionType] = useState<QuestionType>(
    question?.question_type ?? "single_choice",
  )
  const [stem, setStem] = useState(question?.stem ?? "")
  const [optionTexts, setOptionTexts] = useState<string[]>(() =>
    question?.question_type === "single_choice" && question.options?.length
      ? question.options
      : ["", "", "", ""],
  )
  const [correctIndex, setCorrectIndex] = useState(() => {
    if (initialCorrectOption === null) return -1
    const option = initialCorrectOption ?? question?.correct_option
    if (!option) return 0
    const index = LETTERS.findIndex((letter) => letter === option)
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
  const [submitting, setSubmitting] = useState(false)

  const knowledgePointsQuery = useKnowledgePoints()
  const createQuestion = useCreateQuestion()
  const updateQuestion = useUpdateQuestion()
  const pending =
    createQuestion.isPending || updateQuestion.isPending || submitting
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

  function selectCorrectIndex(index: number) {
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

    if (onSubmit) {
      setSubmitting(true)
      try {
        await onSubmit(payload)
        onClose()
      } catch (error) {
        setSubmitError(
          questionErrorMessage(error, "保存失败，请稍后重试。"),
        )
      } finally {
        setSubmitting(false)
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
        onSaved?.(question.question_id, false)
      } else {
        const created = await createQuestion.mutateAsync(payload)
        toast("已保存到我的题库")
        onSaved?.(created.question_id, true)
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
          <DialogTitle>
            {onSubmit
              ? "核对题目"
              : question
                ? "编辑私有题"
                : "新建私有题"}
          </DialogTitle>
          <DialogDescription>
            {onSubmit
              ? "修改后回到导入卡，确认全部题目后再统一保存。"
              : question
                ? "修改只会影响「我的题库」，公共题库保持不变。"
                : "只会保存到「我的题库」，不会修改公共题库。"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <QuestionTypeField value={questionType} onChange={changeType} />

          <QuestionStemField
            value={stem}
            onChange={(value) => {
              setStem(value)
              clearError("stem")
            }}
            error={errors.stem}
          />

          {questionType === "single_choice" && (
            <QuestionOptionsField
              optionTexts={optionTexts}
              correctIndex={correctIndex}
              optionsError={errors.options}
              correctError={errors.correctOption}
              onOptionChange={changeOption}
              onAdd={addOption}
              onRemove={removeOption}
              onCorrectChange={selectCorrectIndex}
            />
          )}

          {questionType === "short_answer" && (
            <QuestionReferenceField
              value={referenceAnswer}
              onChange={(value) => {
                setReferenceAnswer(value)
                clearError("referenceAnswer")
              }}
              error={errors.referenceAnswer}
            />
          )}

          <QuestionKnowledgePointField
            nodes={nodes}
            value={primaryKnowledgePointId}
            isPending={knowledgePointsQuery.isPending}
            isError={knowledgePointsQuery.isError}
            error={errors.primaryKnowledgePointId}
            onSelect={(id) => {
              setPrimaryKnowledgePointId(id)
              clearError("primaryKnowledgePointId")
            }}
          />

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
            {pending
              ? onSubmit
                ? "正在更新…"
                : "保存中…"
              : onSubmit
                ? "更新草稿"
                : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
