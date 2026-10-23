import { useState } from "react";

import { useChatStream } from "../model/chat-stream-context";

type AskHumanPayload = {
  type: "ask_human";
  query: string;
  option_list: string[];
};

function asAskHuman(value: unknown): AskHumanPayload | undefined {
  if (typeof value !== "object" || value === null) return undefined;
  const record = value as Record<string, unknown>;
  if (record.type !== "ask_human") return undefined;
  if (typeof record.query !== "string") return undefined;
  if (!Array.isArray(record.option_list)) return undefined;
  if (!record.option_list.every((item) => typeof item === "string")) {
    return undefined;
  }
  return {
    type: "ask_human",
    query: record.query,
    option_list: record.option_list as string[],
  };
}

function optionLetter(option: string): string {
  const match = /^\s*([A-Za-z])\s*[.、)）]/.exec(option);
  return match?.[1]?.toUpperCase() ?? option.trim();
}

export function AskHumanCard() {
  const stream = useChatStream();
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const interrupt = stream.interrupt;
  if (!interrupt) return null;

  const payload = asAskHuman(interrupt.value);

  if (!payload) {
    return (
      <section className="ask-human" data-testid="ask-human-card">
        <div className="ask-human-eyebrow">Agent 暂停</div>
        <pre className="ask-human-unknown">
          {JSON.stringify(interrupt.value, null, 2)}
        </pre>
      </section>
    );
  }

  const submit = async (option: string) => {
    const letter = optionLetter(option);
    setSubmitting(letter);
    setError(null);
    try {
      await stream.respond(
        { answer: letter },
        interrupt.id ? { interruptId: interrupt.id } : undefined,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(null);
    }
  };

  return (
    <section className="ask-human" data-testid="ask-human-card">
      <div className="ask-human-eyebrow">课堂提问</div>
      <p className="ask-human-query" data-testid="ask-human-query">
        {payload.query}
      </p>
      <div className="ask-human-options">
        {payload.option_list.map((option) => {
          const letter = optionLetter(option);
          const pending = submitting === letter;
          return (
            <button
              key={option}
              type="button"
              className="ask-human-option"
              data-testid="ask-human-option"
              disabled={submitting !== null}
              onClick={() => void submit(option)}
            >
              <span className="ask-human-letter">{letter}</span>
              <span>{option.replace(/^\s*[A-Za-z]\s*[.、)）]\s*/, "")}</span>
              {pending && <span className="ask-human-pending">提交中…</span>}
            </button>
          );
        })}
      </div>
      {submitting !== null && (
        <div className="ask-human-hint" data-testid="ask-human-submitting">
          已提交 {submitting}，等待老师继续…
        </div>
      )}
      {error && <div className="ask-human-error">{error}</div>}
    </section>
  );
}
