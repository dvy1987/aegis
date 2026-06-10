"use client";
import { useEffect, useRef, useState } from "react";
import type { AppealRequest, QuestionTurn } from "@/lib/types";
import type { DataSource } from "@/lib/data/source";
import { Button } from "@/components/Button";
import { cn } from "@/lib/cn";

type Msg = { role: "agent" | "you"; text: string };

/**
 * Turn-based pre-draft interview (appeal flow). A few plain-English questions
 * make the draft stronger; every one is optional and the whole step can be
 * skipped. Answers are traced into the draft context — never graded.
 *
 * Fails soft: if the questions API is unavailable we continue straight to
 * drafting with what we have.
 */
export function QuestionChat({
  req,
  source,
  onFinish,
}: {
  req: AppealRequest;
  source: DataSource;
  onFinish: (interviewId?: string) => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [turn, setTurn] = useState<QuestionTurn | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(true);
  const [failed, setFailed] = useState(false);
  const startedRef = useRef(false);
  const finishedRef = useRef(false);

  function finish(interviewId?: string) {
    if (finishedRef.current) return;
    finishedRef.current = true;
    onFinish(interviewId);
  }

  function applyTurn(t: QuestionTurn) {
    setTurn(t);
    if (t.done) {
      finish(t.interview_id);
      return;
    }
    if (t.question) {
      setMessages((m) => [...m, { role: "agent", text: t.question as string }]);
    }
  }

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    source
      .startQuestions({
        denial_text: req.denial_text,
        clinical_context: req.clinical_context ?? "",
        insurer: req.insurer,
      })
      .then((t) => {
        setBusy(false);
        applyTurn(t);
      })
      .catch(() => {
        setBusy(false);
        setFailed(true);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function send(answer: string) {
    if (!turn || busy) return;
    setMessages((m) => [...m, { role: "you", text: answer || "(skipped this one)" }]);
    setDraft("");
    setBusy(true);
    try {
      applyTurn(await source.answerQuestion(turn.interview_id, answer));
    } catch {
      finish(turn.interview_id);
    } finally {
      setBusy(false);
    }
  }

  async function skipAll() {
    setBusy(true);
    try {
      if (turn) {
        const t = await source.skipQuestions(turn.interview_id);
        finish(t.interview_id);
        return;
      }
    } catch {
      // fall through — draft with what we have
    }
    finish(turn?.interview_id);
  }

  if (failed) {
    return (
      <div className="flex flex-col gap-6">
        <h2 className="font-display text-display-md font-semibold tracking-tight">
          A couple of questions first.
        </h2>
        <p className="max-w-prose font-body text-lg text-text-secondary">
          We couldn&apos;t start the questions right now. No problem — we&apos;ll draft with what
          you&apos;ve already given us.
        </p>
        <div>
          <Button onClick={() => finish(undefined)}>Continue to the draft</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="font-display text-display-md font-semibold tracking-tight">
          A couple of questions first.
        </h2>
        <p className="mt-4 max-w-prose font-body text-lg text-text-secondary">
          Short answers in your own words make the draft stronger. Skip anything you don&apos;t
          know — we&apos;ll note it for later instead.
        </p>
      </div>

      <div
        className="flex min-h-40 flex-col gap-3 rounded-md border border-border-default bg-surface-secondary p-6"
        aria-live="polite"
      >
        {messages.map((m, n) => (
          <p
            key={n}
            className={cn(
              "max-w-prose font-body text-base leading-base",
              m.role === "agent" ? "text-text-primary" : "self-end text-text-secondary",
            )}
          >
            {m.role === "you" && <span className="mr-2 text-text-muted">You:</span>}
            {m.text}
          </p>
        ))}
        {busy && <p className="font-body text-sm text-text-muted">Thinking…</p>}
      </div>

      <div className="flex flex-col gap-3">
        <label htmlFor="question-answer" className="sr-only">
          Your answer
        </label>
        <textarea
          id="question-answer"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(draft.trim());
            }
          }}
          placeholder="Type your answer…"
          disabled={busy || !turn}
          className={cn(
            "min-h-24 w-full rounded-md border border-border-default bg-surface-secondary p-4",
            "font-body text-base text-text-primary placeholder:text-text-muted",
            "focus-visible:outline-2 focus-visible:outline-accent-sage",
          )}
        />
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => void send(draft.trim())} disabled={busy || !turn || !draft.trim()}>
            Send answer
          </Button>
          <button
            type="button"
            onClick={() => void send("I don't know")}
            disabled={busy || !turn}
            className="rounded-pill border border-border-default px-4 py-2 font-body text-sm text-text-secondary hover:border-border-strong focus-visible:outline-2 focus-visible:outline-accent-sage"
          >
            I don&apos;t know
          </button>
          <button
            type="button"
            onClick={() => void skipAll()}
            disabled={busy && !turn}
            className="font-body text-sm text-text-tertiary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-accent-sage"
          >
            Skip the questions — draft now
          </button>
        </div>
      </div>
    </div>
  );
}
