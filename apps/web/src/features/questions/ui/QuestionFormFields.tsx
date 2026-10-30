import { ChevronDown, Plus, X } from "lucide-react"
import { useState } from "react"

import type { KnowledgePoint, QuestionType } from "@/shared/api/types"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover"
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
} from "../model"
import { KnowledgePointTree } from "./KnowledgePointTree"

const TYPE_CHOICES = [
  { id: "single_choice", label: "单选" },
  { id: "short_answer", label: "简答" },
] as const satisfies readonly { id: QuestionType; label: string }[]

export function QuestionTypeField({
  value,
  onChange,
}: {
  value: QuestionType
  onChange: (value: QuestionType) => void
}) {
  return (
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
            aria-pressed={value === item.id}
            onClick={() => onChange(item.id)}
            className={cn(
              "h-9 rounded-sm border text-[12.5px] font-medium transition-colors sm:h-8",
              value === item.id
                ? "border-line bg-surface text-ink"
                : "border-transparent text-ink-muted hover:text-ink",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export function QuestionStemField({
  value,
  onChange,
  error,
}: {
  value: string
  onChange: (value: string) => void
  error?: string
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="question-stem">题干</Label>
      <Textarea
        id="question-stem"
        name="stem"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={3}
        maxLength={STEM_MAX_LENGTH}
        placeholder="用一句话描述问题…"
        autoComplete="off"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? "question-stem-error" : undefined}
        className="min-h-24 text-[16px] sm:text-[14px]"
      />
      {error && (
        <p
          id="question-stem-error"
          role="alert"
          className="text-[12px] text-danger"
        >
          {error}
        </p>
      )}
    </div>
  )
}

export function QuestionOptionsField({
  optionTexts,
  correctIndex,
  optionsError,
  correctError,
  onOptionChange,
  onAdd,
  onRemove,
  onCorrectChange,
}: {
  optionTexts: string[]
  correctIndex: number
  optionsError?: string
  correctError?: string
  onOptionChange: (index: number, value: string) => void
  onAdd: () => void
  onRemove: (index: number) => void
  onCorrectChange: (index: number) => void
}) {
  return (
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
                onChange={(event) => onOptionChange(index, event.target.value)}
                placeholder={`选项 ${LETTERS[index]}`}
                aria-label={`选项 ${LETTERS[index]}`}
                aria-invalid={Boolean(optionsError)}
                aria-describedby={
                  optionsError ? "question-options-error" : undefined
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
                onClick={() => onRemove(index)}
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
            onClick={onAdd}
          >
            <Plus className="size-3.5" aria-hidden="true" />
            添加选项
          </Button>
        )}
        {optionsError && (
          <p
            id="question-options-error"
            role="alert"
            className="text-[12px] text-danger"
          >
            {optionsError}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="correct-option">正确答案</Label>
        <Select
          value={correctIndex >= 0 ? LETTERS[correctIndex] : undefined}
          onValueChange={(letter) => {
            const index = LETTERS.findIndex((item) => item === letter)
            if (index >= 0) onCorrectChange(index)
          }}
        >
          <SelectTrigger
            id="correct-option"
            aria-describedby={
              correctError ? "question-correct-option-error" : undefined
            }
            className="w-28"
          >
            <SelectValue placeholder="选择" />
          </SelectTrigger>
          <SelectContent>
            {optionTexts.map((_, index) => (
              <SelectItem key={LETTERS[index]} value={LETTERS[index]}>
                {LETTERS[index]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {correctError && (
          <p
            id="question-correct-option-error"
            role="alert"
            className="text-[12px] text-danger"
          >
            {correctError}
          </p>
        )}
      </div>
    </>
  )
}

export function QuestionReferenceField({
  value,
  onChange,
  error,
}: {
  value: string
  onChange: (value: string) => void
  error?: string
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="reference-answer">参考答案</Label>
      <Textarea
        id="reference-answer"
        name="reference-answer"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        maxLength={REFERENCE_MAX_LENGTH}
        placeholder="可以留空，之后在对话里补充。"
        autoComplete="off"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? "reference-answer-error" : undefined}
        className="text-[16px] sm:text-[14px]"
      />
      {error && (
        <p
          id="reference-answer-error"
          role="alert"
          className="text-[12px] text-danger"
        >
          {error}
        </p>
      )}
    </div>
  )
}

export function QuestionKnowledgePointField({
  nodes,
  value,
  isPending,
  isError,
  error,
  onSelect,
}: {
  nodes: KnowledgePoint[]
  value: string
  isPending: boolean
  isError: boolean
  error?: string
  onSelect: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const selected = nodes.find((node) => node.id === value)

  return (
    <div className="space-y-1.5">
      <Label htmlFor="question-primary-kp">主知识点</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            id="question-primary-kp"
            disabled={isPending || isError}
            aria-describedby={
              error ? "question-primary-kp-error" : undefined
            }
            className={cn(
              "h-10 w-full justify-between gap-1.5 px-3 text-[13px] font-normal sm:h-9",
              selected ? "text-ink" : "text-ink-muted",
            )}
          >
            <span className="flex min-w-0 items-center gap-2">
              <span className="truncate">
                {selected
                  ? `${selected.id} ${selected.title}`
                  : isPending
                    ? "正在加载知识点…"
                    : "选择主知识点"}
              </span>
            </span>
            <ChevronDown
              className="size-3.5 shrink-0 text-ink-muted"
              aria-hidden="true"
            />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          align="start"
          className="w-[min(360px,calc(100vw-2rem))] p-1.5"
        >
          <div className="scroll-slim max-h-72 overflow-y-auto">
            <KnowledgePointTree
              nodes={nodes}
              value={value || undefined}
              onSelect={(id) => {
                onSelect(id)
                setOpen(false)
              }}
            />
          </div>
        </PopoverContent>
      </Popover>
      {isError && (
        <p role="alert" className="text-[12px] text-danger">
          知识点目录加载失败，请关闭后重试。
        </p>
      )}
      {error && (
        <p
          id="question-primary-kp-error"
          role="alert"
          className="text-[12px] text-danger"
        >
          {error}
        </p>
      )}
    </div>
  )
}
