"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { ShowcaseManifest, ShowcaseRunSession } from "@/lib/types";
import { BEAT_MS, useTheatrical } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { VerdictCell } from "./VerdictCell";

type Tab = "quick" | "serious";

/**
 * The signature widget. Demo / Serious act as tabs (sliding accent underline);
 * each shows Pre-training / Training[before·after] / Post-training. Cells light
 * up as poll data arrives. Same data the old matrix consumed — restyled only.
 */
export function LearningMatrix({
  manifest,
  session,
}: {
  manifest: ShowcaseManifest | null;
  session: ShowcaseRunSession | null;
}) {
  const reduce = useReducedMotion();
  const { runMoment } = useTheatrical();
  const ignitedSession = useRef<string | null>(null);
  const [matrixIgnite, setMatrixIgnite] = useState(false);
  const sessionTab: Tab | null = session?.run_type ?? null;
  const [tab, setTab] = useState<Tab>(sessionTab ?? "quick");
  // Auto-follow the live run's cohort (React render-phase "adjust state on prop
  // change" pattern — avoids a setState-in-effect cascade).
  const [seenSessionTab, setSeenSessionTab] = useState<Tab | null>(sessionTab);
  if (sessionTab !== seenSessionTab) {
    setSeenSessionTab(sessionTab);
    if (sessionTab) setTab(sessionTab);
  }
  const tabSession = session?.run_type === tab ? session : null;

  useEffect(() => {
    if (reduce || !session?.session_id) return;
    if (ignitedSession.current === session.session_id) return;
    ignitedSession.current = session.session_id;
    runMoment(
      "run-ignite",
      () => setMatrixIgnite(true),
      BEAT_MS,
    );
    const off = window.setTimeout(() => setMatrixIgnite(false), BEAT_MS + 200);
    return () => window.clearTimeout(off);
  }, [reduce, runMoment, session?.session_id]);

  const tabs: { key: Tab; label: string; subtitle: string; locked: string }[] = [
    {
      key: "quick",
      label: "Demo",
      subtitle: manifest
        ? `${manifest.quick_train.length} train · ${manifest.quick_holdout.length} holdout`
        : "Quick check",
      locked: "Run quick check to populate this view.",
    },
    {
      key: "serious",
      label: "Serious",
      subtitle: manifest
        ? `${manifest.serious_train_count} train · ${manifest.serious_holdout.length} holdout`
        : "Serious pass",
      locked: "Locked until the quick check succeeds.",
    },
  ];
  const activeMeta = tabs.find((t) => t.key === tab)!;

  return (
    <section
      data-theatrical-zone="run-ignite"
      className={matrixIgnite ? "sc-matrix-ignite flex flex-col gap-5" : "flex flex-col gap-5"}
    >
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <MonoLabel>Learning matrix</MonoLabel>
          <h3 className="sc-h2" style={{ fontSize: "1.5rem" }}>
            Evidence as it arrives
          </h3>
        </div>
        {tabSession && (
          <span
            className="rounded-full px-3 py-1 sc-mono"
            style={{ border: "1px solid var(--sc-hairline)", color: "var(--sc-text-2)" }}
          >
            {tabSession.status.replaceAll("_", " ")}
          </span>
        )}
      </div>

      {/* tabs */}
      <div className="flex gap-1" role="tablist" aria-label="Run cohort">
        {tabs.map((t) => {
          const isActive = t.key === tab;
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={isActive}
              onClick={() => setTab(t.key)}
              className="relative px-4 py-2 text-left focus-visible:outline-2 focus-visible:outline-offset-2"
              style={{ outlineColor: "var(--sc-accent)" }}
            >
              <span
                className="block sc-serif"
                style={{
                  fontSize: "1.05rem",
                  color: isActive ? "var(--sc-text)" : "var(--sc-text-3)",
                }}
              >
                {t.label}
              </span>
              <span className="block sc-mono" style={{ marginTop: 2 }}>
                {t.subtitle}
              </span>
              {isActive && (
                <motion.span
                  layoutId="sc-matrix-underline"
                  className="absolute -bottom-px left-0 h-0.5 w-full"
                  style={{ background: "var(--sc-accent)", boxShadow: "0 0 8px var(--sc-accent-glow)" }}
                />
              )}
            </button>
          );
        })}
      </div>
      <hr className="sc-divider" />

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="grid gap-3"
        >
          <StageBox
            title="Pre-training"
            caption="Held-out baseline · current prompt"
            results={tabSession?.pre_measure_results ?? []}
            emptyMessage={tabSession ? "Waiting for held-out measurement." : activeMeta.locked}
          />
          <TrainingBox
            before={tabSession?.training_pre_measure_results ?? []}
            after={tabSession?.training_post_measure_results ?? []}
            emptyMessage={tabSession ? "Waiting for training measurements." : activeMeta.locked}
          />
          <StageBox
            title="Post-training"
            caption="Held-out · promoted prompt"
            results={tabSession?.post_measure_results ?? []}
            emptyMessage={tabSession ? "Waiting for approval." : activeMeta.locked}
          />
        </motion.div>
      </AnimatePresence>
    </section>
  );
}

function readCell(result: Record<string, unknown>, index: number) {
  return {
    verdict: String(result.verdict ?? ""),
    caseId: String(result.case_id ?? `case_${index + 1}`),
  };
}

function CellGrid({ results, rowLabel }: { results: Record<string, unknown>[]; rowLabel?: string }) {
  return (
    <div className="flex items-center gap-2">
      {rowLabel && (
        <span className="w-14 shrink-0 sc-mono" aria-hidden>
          {rowLabel}
        </span>
      )}
      <div className="grid max-h-36 flex-1 grid-cols-[repeat(auto-fill,minmax(1.25rem,1fr))] gap-1 overflow-auto">
        {results.map((r, i) => {
          const { verdict, caseId } = readCell(r, i);
          return <VerdictCell key={`${caseId}-${i}`} verdict={verdict} caseId={caseId} index={i} />;
        })}
      </div>
    </div>
  );
}

function StageBox({
  title,
  caption,
  results,
  emptyMessage,
}: {
  title: string;
  caption: string;
  results: Record<string, unknown>[];
  emptyMessage: string;
}) {
  return (
    <div className="sc-panel-sunken p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <h4 className="sc-serif" style={{ fontSize: "0.95rem", color: "var(--sc-text)" }}>
            {title}
          </h4>
          <span className="sc-mono">{caption}</span>
        </div>
        {results.length > 0 && (
          <span className="sc-mono">
            {results.length} {results.length === 1 ? "case" : "cases"}
          </span>
        )}
      </div>
      {results.length > 0 ? (
        <CellGrid results={results} />
      ) : (
        <p className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-3)" }}>
          {emptyMessage}
        </p>
      )}
    </div>
  );
}

function TrainingBox({
  before,
  after,
  emptyMessage,
}: {
  before: Record<string, unknown>[];
  after: Record<string, unknown>[];
  emptyMessage: string;
}) {
  const hasData = before.length > 0 || after.length > 0;
  return (
    <div className="sc-panel-sunken p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <h4 className="sc-serif" style={{ fontSize: "0.95rem", color: "var(--sc-text)" }}>
            Training
          </h4>
          <span className="sc-mono">Train set · before vs after learning</span>
        </div>
      </div>
      {hasData ? (
        <div className="grid gap-2">
          <CellGrid results={before} rowLabel="Before" />
          <CellGrid results={after} rowLabel="After" />
        </div>
      ) : (
        <p className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-3)" }}>
          {emptyMessage}
        </p>
      )}
    </div>
  );
}
