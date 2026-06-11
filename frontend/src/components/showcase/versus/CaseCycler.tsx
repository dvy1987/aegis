"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { CaseSummary } from "@/lib/types";
import { cn } from "@/lib/cn";
import {
  CASE_CLINICAL_CONTEXT_MODAL_EYEBROW,
  CASE_CLINICAL_CONTEXT_PILL,
  CASE_CYCLER_LABEL,
  CASE_DENIAL_LETTER_MODAL_EYEBROW,
  CASE_DENIAL_LETTER_PILL,
} from "@/components/showcase/copy";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { CaseDocumentModal, type CaseDocumentKind } from "./CaseDocumentModal";

/**
 * Replaces the old pill row. One featured case presented cinematically, with a
 * quiet prev/next cycler + dot filmstrip. Drives the existing `setSel` — the
 * `getShowcase(sel)` data flow is untouched.
 */
export function CaseCycler({
  cases,
  selected,
  onSelect,
}: {
  cases: CaseSummary[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const [documentView, setDocumentView] = useState<CaseDocumentKind | null>(null);
  const idx = cases.length === 0 ? 0 : Math.max(0, cases.findIndex((c) => c.case_id === selected));
  const current = cases[idx];

  useEffect(() => {
    setDocumentView(null);
  }, [current?.case_id]);

  if (cases.length === 0 || !current) return null;

  const go = (delta: number) => {
    const next = (idx + delta + cases.length) % cases.length;
    onSelect(cases[next].case_id);
  };

  const modalTitle =
    documentView === "denial"
      ? CASE_DENIAL_LETTER_PILL
      : documentView === "clinical"
        ? CASE_CLINICAL_CONTEXT_PILL
        : "";
  const modalEyebrow =
    documentView === "denial"
      ? CASE_DENIAL_LETTER_MODAL_EYEBROW
      : documentView === "clinical"
        ? CASE_CLINICAL_CONTEXT_MODAL_EYEBROW
        : "";
  const modalBody =
    documentView === "denial"
      ? current.denial_letter_text
      : documentView === "clinical"
        ? (current.clinical_context ?? "")
        : "";

  return (
    <>
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4">
          <MonoLabel>
            {CASE_CYCLER_LABEL} · {idx + 1} / {cases.length}
          </MonoLabel>
          <div className="flex items-center gap-2">
            <CyclerButton label="Previous case" onClick={() => go(-1)} dir="prev" />
            <CyclerButton label="Next case" onClick={() => go(1)} dir="next" />
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={current.case_id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
          >
            <h3 className="sc-h2" style={{ fontSize: "1.6rem" }}>
              {current.insurer} · {current.denial_type}
            </h3>
            <p className="mt-1 sc-body" style={{ fontSize: "0.95rem", color: "var(--sc-text-2)" }}>
              {current.headline}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <DocumentPill
                label={CASE_DENIAL_LETTER_PILL}
                active={documentView === "denial"}
                onClick={() => setDocumentView("denial")}
              />
              <DocumentPill
                label={CASE_CLINICAL_CONTEXT_PILL}
                active={documentView === "clinical"}
                onClick={() => setDocumentView("clinical")}
              />
            </div>
          </motion.div>
        </AnimatePresence>

        {/* filmstrip */}
        <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Cases">
          {cases.map((c) => {
            const active = c.case_id === current.case_id;
            return (
              <button
                key={c.case_id}
                role="tab"
                aria-selected={active}
                aria-label={`${c.insurer} · ${c.denial_type}`}
                onClick={() => onSelect(c.case_id)}
                className="h-2.5 rounded-full transition-all focus-visible:outline-2 focus-visible:outline-offset-2"
                style={{
                  width: active ? 28 : 10,
                  background: active ? "var(--sc-accent)" : "var(--sc-hairline-strong)",
                  boxShadow: active ? "0 0 8px var(--sc-accent-glow)" : "none",
                  outlineColor: "var(--sc-accent)",
                }}
              />
            );
          })}
        </div>
      </div>

      <CaseDocumentModal
        open={documentView !== null}
        title={modalTitle}
        eyebrow={modalEyebrow}
        body={modalBody}
        onClose={() => setDocumentView(null)}
      />
    </>
  );
}

function DocumentPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full px-3 py-1.5 sc-mono transition-colors focus-visible:outline-2 focus-visible:outline-offset-2",
      )}
      style={{
        border: `1px solid ${active ? "var(--sc-accent)" : "var(--sc-hairline-strong)"}`,
        color: active ? "var(--sc-accent)" : "var(--sc-text-2)",
        background: active ? "color-mix(in oklch, var(--sc-accent) 12%, transparent)" : "transparent",
        boxShadow: active ? "0 0 10px var(--sc-accent-glow)" : "none",
        outlineColor: "var(--sc-accent)",
      }}
    >
      {label}
    </button>
  );
}

function CyclerButton({
  label,
  onClick,
  dir,
}: {
  label: string;
  onClick: () => void;
  dir: "prev" | "next";
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2",
      )}
      style={{ border: "1px solid var(--sc-hairline-strong)", color: "var(--sc-text-2)", outlineColor: "var(--sc-accent)" }}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        {dir === "prev" ? <path d="M15 18l-6-6 6-6" /> : <path d="M9 18l6-6-6-6" />}
      </svg>
    </button>
  );
}
