"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import {
  formatPlaybookList,
  type PromotionPreview,
  type PromotionPreviewSection,
  type PromotionRuleChange,
} from "@/lib/promotionPreview";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";
import {
  APPROVE_CTA,
  PROMOTION_REVIEW_EYEBROW,
  PROMOTION_REVIEW_HEADLINE,
  PROMOTION_REVIEW_LEAD,
  REJECT_CTA,
} from "@/components/showcase/copy";

export function PromotionReviewModal({
  open,
  preview,
  onClose,
  onApprove,
  onReject,
  busy,
  runsEnabled = true,
}: {
  open: boolean;
  preview: PromotionPreview | null;
  onClose: () => void;
  onApprove: () => void;
  onReject: () => void;
  busy?: boolean;
  runsEnabled?: boolean;
}) {
  const reduce = useReducedMotion();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  if (!preview) return null;

  const { lift } = preview;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[80] flex items-end justify-center p-4 sm:items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0 : 0.25 }}
          role="presentation"
        >
          <button
            type="button"
            aria-label="Close review"
            className="absolute inset-0 cursor-default"
            style={{ background: "oklch(0% 0 0 / 0.62)" }}
            onClick={busy ? undefined : onClose}
          />

          <motion.div
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="promotion-review-title"
            className="relative z-[81] flex w-full max-w-3xl flex-col outline-none"
            style={{ maxHeight: "min(88dvh, 52rem)" }}
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.99 }}
            transition={{ duration: reduce ? 0 : 0.45, ease: EASE_OUT_EXPO }}
          >
            <GlassPanel variant="elevated" className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <header
                className="shrink-0 border-b px-6 py-5"
                style={{ borderColor: "var(--sc-hairline)" }}
              >
                <MonoLabel>{PROMOTION_REVIEW_EYEBROW}</MonoLabel>
                <h2 id="promotion-review-title" className="mt-2 sc-h2" style={{ fontSize: "1.65rem" }}>
                  {PROMOTION_REVIEW_HEADLINE}
                </h2>
                <p className="mt-2 sc-body" style={{ fontSize: "0.95rem", color: "var(--sc-text-2)" }}>
                  {PROMOTION_REVIEW_LEAD}
                </p>
                <LiftSummary lift={lift} />
              </header>

              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
                <div className="flex flex-col gap-6">
                  {preview.sections.length === 0 ? (
                    <p className="sc-body" style={{ color: "var(--sc-text-2)" }}>
                      No component changes were detected in this proposal.
                    </p>
                  ) : (
                    preview.sections.map((section) => (
                      <SectionBlock key={`${section.kind}-${section.title}`} section={section} />
                    ))
                  )}
                </div>
              </div>

              <footer
                className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t px-6 py-4"
                style={{ borderColor: "var(--sc-hairline)" }}
              >
                <p className="sc-mono" style={{ color: "var(--sc-text-3)", fontSize: "0.75rem" }}>
                  {lift.is_promotable ? "Passes promotion gates" : "Blocked by promotion gates"}
                </p>
                <div className="flex flex-wrap gap-3">
                  <IgniteButton variant="ghost" onClick={onClose} disabled={busy}>
                    Close
                  </IgniteButton>
                  <IgniteButton variant="secondary" onClick={onReject} disabled={busy}>
                    {REJECT_CTA}
                  </IgniteButton>
                  <IgniteButton
                    variant="primary"
                    onClick={onApprove}
                    disabled={busy || !runsEnabled || !lift.is_promotable}
                  >
                    {APPROVE_CTA}
                  </IgniteButton>
                </div>
              </footer>
            </GlassPanel>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function LiftSummary({ lift }: { lift: PromotionPreview["lift"] }) {
  return (
    <div
      className="mt-4 grid gap-3 rounded-md p-4 sm:grid-cols-2"
      style={{
        background: "var(--sc-bg-sunken)",
        border: "1px solid var(--sc-hairline)",
      }}
    >
      <div>
        <MonoLabel>Composite lift</MonoLabel>
        <p className="mt-1 sc-serif" style={{ fontSize: "1.25rem", color: "var(--sc-text)" }}>
          {lift.before_composite.toFixed(2)} → {lift.after_composite.toFixed(2)}
          <span className="sc-mono ml-2" style={{ color: "var(--sc-accent)", fontSize: "0.9rem" }}>
            {lift.delta >= 0 ? "+" : ""}
            {lift.delta.toFixed(2)}
          </span>
        </p>
      </div>
      <div>
        <MonoLabel>Summary</MonoLabel>
        <p className="mt-1 sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text-2)" }}>
          {lift.diff_summary || "—"}
        </p>
      </div>
      {lift.vetoes.length > 0 && (
        <div className="sm:col-span-2">
          <MonoLabel>Vetoes</MonoLabel>
          <ul className="mt-1 list-disc pl-5 sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-deny)" }}>
            {lift.vetoes.map((veto) => (
              <li key={veto}>{veto}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SectionBlock({ section }: { section: PromotionPreviewSection }) {
  if (section.kind === "drafter" || section.kind === "question_agent") {
    return (
      <article className="flex flex-col gap-3">
        <SectionHeader title={section.title} versions={`${section.before_version} → ${section.after_version}`} />
        <TextDiff before={section.before_text} after={section.after_text} />
      </article>
    );
  }

  if (section.kind === "us_playbook") {
    return (
      <article className="flex flex-col gap-3">
        <SectionHeader title={section.title} versions={`${section.before_version} → ${section.after_version}`} />
        {section.rule_changes.length === 0 ? (
          <PlaybookJsonBlock playbook={section.after_playbook} />
        ) : (
          <ul className="flex flex-col gap-3">
            {section.rule_changes.map((change) => (
              <RuleChangeCard key={`${change.rule_id}-${change.change}`} change={change} />
            ))}
          </ul>
        )}
      </article>
    );
  }

  return (
    <article className="flex flex-col gap-3">
      <SectionHeader title={section.title} versions={`${section.before_version} → ${section.after_version}`} />
      <PlaybookDiff
        before={section.before_playbook}
        after={section.after_playbook}
      />
    </article>
  );
}

function SectionHeader({ title, versions }: { title: string; versions: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h3 className="sc-serif" style={{ fontSize: "1.15rem", color: "var(--sc-text)" }}>
        {title}
      </h3>
      <span className="sc-mono" style={{ color: "var(--sc-text-3)", fontSize: "0.75rem" }}>
        {versions}
      </span>
    </div>
  );
}

function RuleChangeCard({ change }: { change: PromotionRuleChange }) {
  const tone =
    change.change === "appended"
      ? "var(--sc-accent)"
      : change.change === "edited"
        ? "var(--sc-warn)"
        : "var(--sc-deny)";

  return (
    <li
      className="flex flex-col gap-2 rounded-md p-4"
      style={{ border: "1px solid var(--sc-hairline)", background: "var(--sc-bg-sunken)" }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="sc-mono uppercase" style={{ color: tone, fontSize: "0.7rem" }}>
          {change.change}
        </span>
        <span className="sc-mono" style={{ color: "var(--sc-text-3)", fontSize: "0.75rem" }}>
          {change.rule_id}
        </span>
        <span
          className="rounded-full px-2 py-0.5 sc-mono"
          style={{
            fontSize: "0.68rem",
            border: "1px solid var(--sc-hairline)",
            color: "var(--sc-text-2)",
          }}
        >
          {change.scope}
        </span>
        {change.funding_scope && (
          <span className="sc-mono" style={{ fontSize: "0.68rem", color: "var(--sc-text-3)" }}>
            {change.funding_scope}
          </span>
        )}
      </div>
      {change.before_text && (
        <div>
          <MonoLabel>Before</MonoLabel>
          <p className="mt-1 whitespace-pre-wrap sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text-3)" }}>
            {change.before_text}
          </p>
        </div>
      )}
      {change.text && (
        <div>
          <MonoLabel>{change.change === "appended" ? "New rule" : "After"}</MonoLabel>
          <p className="mt-1 whitespace-pre-wrap sc-body" style={{ fontSize: "0.92rem", color: "var(--sc-text)" }}>
            {change.text}
          </p>
        </div>
      )}
      {change.notice && (
        <p className="sc-body" style={{ fontSize: "0.85rem", color: "var(--sc-warn)" }}>
          {change.notice}
        </p>
      )}
      {change.justification && (
        <div>
          <MonoLabel>Why</MonoLabel>
          <p className="mt-1 whitespace-pre-wrap sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-2)" }}>
            {change.justification}
          </p>
        </div>
      )}
    </li>
  );
}

function PlaybookDiff({
  before,
  after,
}: {
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
}) {
  const beforeTactics = formatPlaybookList(before, "tactics");
  const afterTactics = formatPlaybookList(after, "tactics");
  const tacticsChanged = JSON.stringify(beforeTactics) !== JSON.stringify(afterTactics);

  return (
    <div className="flex flex-col gap-4">
      {tacticsChanged && (
        <div className="grid gap-4 md:grid-cols-2">
          <PlaybookColumn label="Before tactics" items={beforeTactics} />
          <PlaybookColumn label="After tactics" items={afterTactics} accent />
        </div>
      )}
      {!tacticsChanged && <PlaybookJsonBlock playbook={after} />}
    </div>
  );
}

function PlaybookColumn({ label, items, accent }: { label: string; items: string[]; accent?: boolean }) {
  return (
    <div
      className="rounded-md p-4"
      style={{
        border: `1px solid ${accent ? "color-mix(in oklch, var(--sc-accent) 35%, var(--sc-hairline))" : "var(--sc-hairline)"}`,
        background: "var(--sc-bg-sunken)",
      }}
    >
      <MonoLabel>{label}</MonoLabel>
      <ul className="mt-2 flex flex-col gap-2">
        {items.length === 0 ? (
          <li className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-3)" }}>
            —
          </li>
        ) : (
          items.map((item) => (
            <li key={item} className="sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text)" }}>
              {item}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function PlaybookJsonBlock({ playbook }: { playbook?: Record<string, unknown> | null }) {
  if (!playbook) return null;
  return (
    <pre
      className="overflow-x-auto rounded-md p-4 sc-mono"
      style={{
        fontSize: "0.78rem",
        lineHeight: 1.5,
        color: "var(--sc-text-2)",
        background: "var(--sc-bg-sunken)",
        border: "1px solid var(--sc-hairline)",
      }}
    >
      {JSON.stringify(playbook, null, 2)}
    </pre>
  );
}

function TextDiff({ before, after }: { before: string; after: string }) {
  if (before === after) {
    return (
      <pre
        className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md p-4 sc-body"
        style={{
          fontSize: "0.88rem",
          lineHeight: 1.55,
          color: "var(--sc-text)",
          background: "var(--sc-bg-sunken)",
          border: "1px solid var(--sc-hairline)",
        }}
      >
        {after}
      </pre>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <MonoLabel>Before</MonoLabel>
        <pre
          className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-md p-4 sc-body"
          style={{
            fontSize: "0.85rem",
            lineHeight: 1.55,
            color: "var(--sc-text-3)",
            background: "var(--sc-bg-sunken)",
            border: "1px solid var(--sc-hairline)",
          }}
        >
          {before || "—"}
        </pre>
      </div>
      <div>
        <MonoLabel>After</MonoLabel>
        <pre
          className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-md p-4 sc-body"
          style={{
            fontSize: "0.88rem",
            lineHeight: 1.55,
            color: "var(--sc-text)",
            background: "var(--sc-bg-sunken)",
            border: "1px solid color-mix(in oklch, var(--sc-accent) 28%, var(--sc-hairline))",
          }}
        >
          {after || "—"}
        </pre>
      </div>
    </div>
  );
}
