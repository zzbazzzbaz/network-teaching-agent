import { useState } from "react";

import { useSandbox } from "@/features/sandbox";

import { useChatStream } from "../model/chat-stream-context";
import { MarkdownContent } from "./MarkdownContent";

type SingleChoicePayload = {
  type: "ask_student";
  mode: "single_choice";
  question: string;
  options: string[];
};

type ShortAnswerPayload = {
  type: "ask_student";
  mode: "short_answer";
  question: string;
  placeholder?: string;
};

type AskStudentPayload = SingleChoicePayload | ShortAnswerPayload;

function asAskStudent(value: unknown): AskStudentPayload | undefined {
  if (typeof value !== "object" || value === null) return undefined;
  const record = value as Record<string, unknown>;
  if (record.type !== "ask_student") return undefined;
  if (typeof record.question !== "string") return undefined;

  if (record.mode === "single_choice") {
    if (!Array.isArray(record.options)) return undefined;
    if (record.options.length < 2 || record.options.length > 6) return undefined;
    if (!record.options.every((item) => typeof item === "string")) {
      return undefined;
    }
    return {
      type: "ask_student",
      mode: "single_choice",
      question: record.question,
      options: record.options as string[],
    };
  }

  if (record.mode === "short_answer") {
    if (record.options !== undefined && record.options !== null) return undefined;
    return {
      type: "ask_student",
      mode: "short_answer",
      question: record.question,
      placeholder:
        typeof record.placeholder === "string" ? record.placeholder : undefined,
    };
  }

  return undefined;
}

function optionLetter(option: string): string {
  const match = /^\s*([A-Za-z])\s*[.、)）]/.exec(option);
  return match?.[1]?.toUpperCase() ?? option.trim();
}

export function AskStudentCard() {
  const stream = useChatStream();
  const sandbox = useSandbox();
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);

  const interrupt = stream.interrupt;
  if (!interrupt) return null;

  const payload = asAskStudent(interrupt.value);

  if (!payload) {
    return (
      <section className="ask-student" data-testid="ask-student-card">
        <div className="ask-student-eyebrow">Agent 暂停</div>
        <pre className="ask-student-unknown">
          {JSON.stringify(interrupt.value, null, 2)}
        </pre>
      </section>
    );
  }

  const respond = async (value: string, pendingLabel: string) => {
    setSubmitting(pendingLabel);
    setError(null);
    try {
      const responseOptions = interrupt.id ? { interruptId: interrupt.id } : {};
      await stream.respond({ answer: value }, responseOptions);
      void sandbox.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(null);
    }
  };

  const submitChoice = (option: string) => {
    void respond(optionLetter(option), optionLetter(option));
  };

  const submitAnswer = () => {
    const trimmed = answer.trim();
    if (!trimmed || submitting !== null) return;
    void respond(trimmed, "text");
  };

  return (
    <section className="ask-student" data-testid="ask-student-card">
      <div className="ask-student-eyebrow">课堂提问</div>
      <MarkdownContent
        content={payload.question}
        className="ask-student-query"
        testId="ask-student-query"
      />

      {payload.mode === "single_choice" ? (
        <div className="ask-student-options" data-testid="ask-student-options">
          {payload.options.map((option) => {
            const letter = optionLetter(option);
            const pending = submitting === letter;
            return (
              <button
                key={option}
                type="button"
                className="ask-student-option"
                data-testid="ask-student-option"
                disabled={submitting !== null}
                onClick={() => submitChoice(option)}
              >
                <span className="ask-student-letter">{letter}</span>
                <span>
                  {option.replace(/^\s*[A-Za-z]\s*[.、)）]\s*/, "")}
                </span>
                {pending && <span className="ask-student-pending">提交中…</span>}
              </button>
            );
          })}
        </div>
      ) : (
        <form
          className="ask-student-form"
          onSubmit={(event) => {
            event.preventDefault();
            submitAnswer();
          }}
        >
          <textarea
            className="ask-student-answer"
            data-testid="ask-student-answer"
            aria-label="简答题答案"
            placeholder={payload.placeholder || "输入你的答案"}
            value={answer}
            maxLength={2000}
            rows={3}
            disabled={submitting !== null}
            onChange={(event) => setAnswer(event.target.value)}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <div className="ask-student-actions">
            <button
              type="submit"
              className="ask-student-submit"
              data-testid="ask-student-submit"
              disabled={submitting !== null || answer.trim().length === 0}
            >
              {submitting === "text" ? "提交中…" : "提交答案"}
            </button>
          </div>
        </form>
      )}

      {submitting !== null && (
        <div className="ask-student-hint" data-testid="ask-student-submitting">
          {payload.mode === "single_choice" && submitting !== "text"
            ? `已提交 ${submitting}，等待老师继续…`
            : "已提交，等待老师继续…"}
        </div>
      )}
      {error && (
        <div className="ask-student-error" data-testid="ask-student-error">
          {error}
        </div>
      )}
    </section>
  );
}
