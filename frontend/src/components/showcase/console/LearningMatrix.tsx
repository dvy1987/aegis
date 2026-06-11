"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { ShowcaseManifest, ShowcaseRunSession } from "@/lib/types";
import { BEAT_MS, useTheatrical } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import {
  MATRIX_EYEBROW,
  MATRIX_HEADLINE,
  MATRIX_POST_CAPTION,
  MATRIX_POST_TITLE,
  MATRIX_PRE_CAPTION,
  MATRIX_PRE_TITLE,
  MATRIX_QUICK_LOCKED,
  MATRIX_SERIOUS_LOCKED,
  MATRIX_TAB_DEMO,
  MATRIX_TAB_SERIOUS,
  MATRIX_TRAIN_AFTER_CAPTION,
  MATRIX_TRAIN_AFTER_TITLE,
  MATRIX_TRAIN_BEFORE_CAPTION,
  MATRIX_TRAIN_BEFORE_TITLE,
  MATRIX_WAIT_POST,
  MATRIX_WAIT_PRE,
  MATRIX_WAIT_TRAIN,
} from "@/components/showcase/copy";
import {
  mergeResultSlots,
  productionRowColumns,
  resolveMatrixCohort,
  type MatrixSlot,
  type MatrixTab,
} from "./matrixSlots";
import { VerdictCell } from "./VerdictCell";

/**
 * Evidence grid — fixed slot counts from manifest (preview: 1 holdout + 3 train; production: 2 + 5).
 * Cells stay grey until measured; APPROVE/DENY paint green/red when results land.
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
  const sessionTab: MatrixTab | null = session?.run_type ?? null;
  const [tab, setTab] = useState<MatrixTab>(sessionTab ?? "quick");
  const [seenSessionTab, setSeenSessionTab] = useState<MatrixTab | null>(sessionTab);
  if (sessionTab !== seenSessionTab) {
    setSeenSessionTab(sessionTab);
    if (sessionTab) setTab(sessionTab);
  }
  const tabSession = session?.run_type === tab ? session : null;

  useEffect(() => {
    if (reduce || !session?.session_id) return;
    if (ignitedSession.current === session.session_id) return;
    ignitedSession.current = session.session_id;
    runMoment("run-ignite", () => setMatrixIgnite(true), BEAT_MS);
    const off = window.setTimeout(() => setMatrixIgnite(false), BEAT_MS + 200);
    return () => window.clearTimeout(off);
  }, [reduce, runMoment, session?.session_id]);

  const tabs: { key: MatrixTab; label: string; subtitle: string; locked: string }[] = [
    {
      key: "quick",
      label: MATRIX_TAB_DEMO,
      subtitle: manifest
        ? `${manifest.quick_train.length} training · ${manifest.quick_holdout.length} holdout`
        : "Preview run",
      locked: MATRIX_QUICK_LOCKED,
    },
    {
      key: "serious",
      label: MATRIX_TAB_SERIOUS,
      subtitle: manifest
        ? `${manifest.serious_train_count} training · ${manifest.serious_holdout.length} holdout`
        : "Production run",
      locked: MATRIX_SERIOUS_LOCKED,
    },
  ];
  const activeMeta = tabs.find((t) => t.key === tab)!;
  const cohort =
    manifest != null ? resolveMatrixCohort(manifest, tab, tabSession) : { holdoutIds: [], trainIds: [] };
  const showLockedHint = !tabSession && tab === "serious";

  const preSlots = mergeResultSlots(cohort.holdoutIds, tabSession?.pre_measure_results ?? []);
  const trainBeforeSlots = mergeResultSlots(
    cohort.trainIds,
    tabSession?.training_pre_measure_results ?? [],
  );
  const trainAfterSlots = mergeResultSlots(
    cohort.trainIds,
    tabSession?.training_post_measure_results ?? [],
  );
  const postSlots = mergeResultSlots(cohort.holdoutIds, tabSession?.post_measure_results ?? []);

  return (
    <section
      data-theatrical-zone="run-ignite"
      className={matrixIgnite ? "sc-matrix-ignite flex flex-col gap-5" : "flex flex-col gap-5"}
    >
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <MonoLabel>{MATRIX_EYEBROW}</MonoLabel>
          <h3 className="sc-h2" style={{ fontSize: "1.5rem" }}>
            {MATRIX_HEADLINE}
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
          {showLockedHint && (
            <p className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-3)" }}>
              {activeMeta.locked}
            </p>
          )}

          {!manifest ? (
            <p className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-3)" }}>
              {MATRIX_WAIT_PRE}
            </p>
          ) : (
            <>
              <StageBox
                tab={tab}
                title={MATRIX_PRE_TITLE}
                caption={MATRIX_PRE_CAPTION}
                slots={preSlots}
                waitHint={tabSession ? MATRIX_WAIT_PRE : undefined}
              />
              <TrainingSections
                tab={tab}
                beforeSlots={trainBeforeSlots}
                afterSlots={trainAfterSlots}
                waitHint={tabSession ? MATRIX_WAIT_TRAIN : undefined}
              />
              <StageBox
                tab={tab}
                title={MATRIX_POST_TITLE}
                caption={MATRIX_POST_CAPTION}
                slots={postSlots}
                waitHint={tabSession ? MATRIX_WAIT_POST : undefined}
              />
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}

function CellGrid({ slots, tab }: { slots: MatrixSlot[]; tab: MatrixTab }) {
  if (slots.length === 0) return null;

  const prodCols = productionRowColumns(slots.length, tab);
  if (prodCols == null) {
    return (
      <div
        className="grid max-h-36 grid-cols-[repeat(auto-fill,minmax(1.25rem,1fr))] gap-1 overflow-auto"
        role="list"
        aria-label={`${slots.length} cases`}
      >
        {slots.map((slot, i) => (
          <VerdictCell key={`${slot.caseId}-${i}`} verdict={slot.verdict} caseId={slot.caseId} index={i} />
        ))}
      </div>
    );
  }

  const top = slots.slice(0, prodCols);
  const bottom = slots.slice(prodCols);

  return (
    <div className="max-h-36 overflow-auto" role="list" aria-label={`${slots.length} cases`}>
      <div className="flex w-max flex-col gap-1">
        {[top, bottom].map((row, rowIndex) => (
          <div
            key={rowIndex}
            className="grid gap-1"
            style={{ gridTemplateColumns: `repeat(${prodCols}, 1.25rem)` }}
          >
            {row.map((slot, i) => (
              <VerdictCell
                key={`${slot.caseId}-${rowIndex}-${i}`}
                verdict={slot.verdict}
                caseId={slot.caseId}
                index={rowIndex * prodCols + i}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function StageBox({
  tab,
  title,
  caption,
  slots,
  waitHint,
}: {
  tab: MatrixTab;
  title: string;
  caption: string;
  slots: MatrixSlot[];
  waitHint?: string;
}) {
  const filled = slots.filter((s) => s.verdict).length;
  return (
    <div className="sc-panel-sunken p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <h4 className="sc-serif" style={{ fontSize: "0.95rem", color: "var(--sc-text)" }}>
            {title}
          </h4>
          <span className="sc-mono">{caption}</span>
        </div>
        <span className="sc-mono">
          {filled}/{slots.length} scored
        </span>
      </div>
      <CellGrid slots={slots} tab={tab} />
      {waitHint && filled === 0 && (
        <p className="mt-3 sc-body" style={{ fontSize: "0.8125rem", color: "var(--sc-text-3)" }}>
          {waitHint}
        </p>
      )}
    </div>
  );
}

function TrainingSections({
  tab,
  beforeSlots,
  afterSlots,
  waitHint,
}: {
  tab: MatrixTab;
  beforeSlots: MatrixSlot[];
  afterSlots: MatrixSlot[];
  waitHint?: string;
}) {
  const beforeFilled = beforeSlots.filter((s) => s.verdict).length;
  const afterFilled = afterSlots.filter((s) => s.verdict).length;

  return (
    <div className="grid gap-3">
      <StageBox
        tab={tab}
        title={MATRIX_TRAIN_BEFORE_TITLE}
        caption={MATRIX_TRAIN_BEFORE_CAPTION}
        slots={beforeSlots}
        waitHint={waitHint && beforeFilled === 0 ? waitHint : undefined}
      />
      <StageBox
        tab={tab}
        title={MATRIX_TRAIN_AFTER_TITLE}
        caption={MATRIX_TRAIN_AFTER_CAPTION}
        slots={afterSlots}
        waitHint={waitHint && afterFilled === 0 && beforeFilled > 0 ? waitHint : undefined}
      />
    </div>
  );
}
