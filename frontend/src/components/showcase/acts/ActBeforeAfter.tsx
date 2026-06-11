"use client";

import { motion } from "framer-motion";
import type {
  CaseSummary,
  MeasuredLiftCache,
  ShowcaseBundle,
  ShowcaseMeasureResult,
  ShowcaseMeasureVariant,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { CaseCycler } from "@/components/showcase/versus/CaseCycler";
import { VersusPanel } from "@/components/showcase/versus/VersusPanel";
import { BEFORE_AFTER_EYEBROW, BEFORE_AFTER_HEADLINE } from "@/components/showcase/copy";
import { DiffCard } from "@/components/showcase/versus/DiffCard";

/**
 * Act IV — the money shot. Plain section (no framer-transformed wrapper) so the
 * GSAP ScrollTrigger inside VersusPanel measures cleanly. Case cycling replaces
 * the old pill row.
 */
export function ActBeforeAfter({
  bundle,
  cases,
  selected,
  onSelect,
  previewSession,
  productionSession,
  measuredLift,
  onMeasuredLiftUpdate,
  rollbackTarget,
}: {
  bundle: ShowcaseBundle | null;
  cases: CaseSummary[];
  selected: string;
  onSelect: (id: string) => void;
  previewSession: ShowcaseRunSession | null;
  productionSession: ShowcaseRunSession | null;
  measuredLift: MeasuredLiftCache;
  onMeasuredLiftUpdate: (
    caseId: string,
    variant: ShowcaseMeasureVariant,
    result: ShowcaseMeasureResult,
  ) => void;
  rollbackTarget: ShowcaseRollbackTarget | null;
}) {
  const currentCase = cases.find((c) => c.case_id === selected) ?? cases[0];
  return (
    <section
      id="before-after"
      className="mx-auto flex w-full flex-col gap-10 px-6 py-24 md:px-12 md:py-32"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <motion.div
        className="flex flex-col gap-2"
        initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, amount: 0.6 }}
        transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
      >
        <MonoLabel>{BEFORE_AFTER_EYEBROW}</MonoLabel>
        <h2 className="sc-h2">{BEFORE_AFTER_HEADLINE}</h2>
      </motion.div>

      <CaseCycler cases={cases} selected={selected} onSelect={onSelect} />

      {bundle && currentCase && (
        <>
          <VersusPanel
            key={`versus-${bundle.case_id}`}
            bundle={bundle}
            caseSummary={currentCase}
            previewSession={previewSession}
            productionSession={productionSession}
            measuredLift={measuredLift}
            onMeasuredLiftUpdate={onMeasuredLiftUpdate}
            rollbackTarget={rollbackTarget}
          />
          {bundle.measured && (
            <DiffCard key={`diff-${bundle.case_id}`} whatChanged={bundle.what_changed} />
          )}
        </>
      )}
    </section>
  );
}
