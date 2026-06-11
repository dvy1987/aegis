"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import type { ShowcaseMeasureResult } from "@/lib/types";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import {
  SIMULATOR_MODAL_CRITIQUE,
  SIMULATOR_MODAL_EYEBROW,
  SIMULATOR_MODAL_GAPS,
  SIMULATOR_MODAL_PROXY,
  SIMULATOR_MODAL_FEATURES,
  SIMULATOR_MODAL_SCORE,
} from "@/components/showcase/copy";

export function SimulatorResultModal({
  open,
  result,
  title,
  onClose,
}: {
  open: boolean;
  result: ShowcaseMeasureResult | null;
  title: string;
  onClose: () => void;
}) {
  const reduce = useReducedMotion();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  if (!result) return null;
  const { outcome } = result;
  const approved = outcome.verdict === "APPROVE";
  const tone = approved ? "var(--sc-accent)" : "var(--sc-deny)";
  const pct = Math.max(0, Math.min(1, outcome.score)) * 100;
  const thresholdPct = Math.max(0, Math.min(1, outcome.threshold)) * 100;

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
            aria-label="Close"
            className="absolute inset-0 cursor-default"
            style={{ background: "oklch(0% 0 0 / 0.62)" }}
            onClick={onClose}
          />

          <motion.div
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="simulator-result-title"
            className="relative z-[81] flex w-full max-w-xl flex-col outline-none"
            style={{ maxHeight: "min(88dvh, 36rem)" }}
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.99 }}
            transition={{ duration: reduce ? 0 : 0.45, ease: EASE_OUT_EXPO }}
          >
            <GlassPanel variant="elevated" className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <header
                className="flex shrink-0 items-start justify-between gap-4 border-b px-6 py-5"
                style={{ borderColor: "var(--sc-hairline)" }}
              >
                <div className="min-w-0">
                  <MonoLabel>{SIMULATOR_MODAL_EYEBROW}</MonoLabel>
                  <h2 id="simulator-result-title" className="mt-2 sc-h2" style={{ fontSize: "1.35rem" }}>
                    {title}
                  </h2>
                  <p className="mt-2 sc-mono" style={{ color: tone, fontSize: "0.8rem" }}>
                    {approved ? "APPROVE" : "DENY"} · {result.prompt_version}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close dialog"
                  className="shrink-0 rounded-full px-3 py-1.5 sc-mono transition-colors hover:opacity-80"
                  style={{
                    border: "1px solid var(--sc-hairline-strong)",
                    color: "var(--sc-text-2)",
                  }}
                >
                  Close
                </button>
              </header>

              <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-6 py-5">
                <div className="flex flex-col gap-2">
                  <MonoLabel>{SIMULATOR_MODAL_SCORE}</MonoLabel>
                  <div
                    className="relative h-2 w-full overflow-hidden rounded-full"
                    style={{ background: "var(--sc-bg-sunken)" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${pct}%`, background: tone, boxShadow: `0 0 10px ${tone}` }}
                    />
                    <div
                      className="absolute top-[-2px] h-3 w-px"
                      style={{ left: `${thresholdPct}%`, background: "var(--sc-text-3)" }}
                      aria-hidden
                    />
                  </div>
                  <span className="sc-mono" style={{ color: "var(--sc-text-3)", fontSize: "0.8rem" }}>
                    {outcome.score.toFixed(2)} · threshold {outcome.threshold.toFixed(2)}
                  </span>
                  <p className="sc-body" style={{ fontSize: "0.85rem", color: "var(--sc-text-3)" }}>
                    {SIMULATOR_MODAL_PROXY}
                  </p>
                </div>

                {outcome.feature_scores.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <MonoLabel>{SIMULATOR_MODAL_FEATURES}</MonoLabel>
                    <ul className="flex flex-col gap-1.5">
                      {outcome.feature_scores.map((feature) => (
                        <li
                          key={feature.feature}
                          className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 sc-mono"
                          style={{ fontSize: "0.78rem", color: "var(--sc-text-2)" }}
                        >
                          <span>
                            {feature.feature.replace(/_/g, " ")}
                            {feature.must_have ? " · must-have" : ""}
                          </span>
                          <span style={{ color: feature.anchor >= 5 ? "var(--sc-accent)" : "var(--sc-deny)" }}>
                            anchor {feature.anchor}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {outcome.gaps.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <MonoLabel>{SIMULATOR_MODAL_GAPS}</MonoLabel>
                    <ul className="flex flex-col gap-1.5">
                      {outcome.gaps.map((gap) => (
                        <li key={gap} className="sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text-2)" }}>
                          {gap}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {outcome.critique && (
                  <div className="flex flex-col gap-2">
                    <MonoLabel>{SIMULATOR_MODAL_CRITIQUE}</MonoLabel>
                    <p className="sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text-2)" }}>
                      {outcome.critique}
                    </p>
                  </div>
                )}
              </div>
            </GlassPanel>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
