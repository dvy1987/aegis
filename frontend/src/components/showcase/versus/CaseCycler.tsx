"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { CaseSummary } from "@/lib/types";
import { cn } from "@/lib/cn";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";

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
  if (cases.length === 0) return null;
  const idx = Math.max(0, cases.findIndex((c) => c.case_id === selected));
  const current = cases[idx] ?? cases[0];
  const go = (delta: number) => {
    const next = (idx + delta + cases.length) % cases.length;
    onSelect(cases[next].case_id);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <MonoLabel>
          Featured case · {idx + 1} / {cases.length}
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
