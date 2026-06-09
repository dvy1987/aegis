"use client";

import { useRef } from "react";
import { motion } from "framer-motion";
import type {
  ShowcaseManifest,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import { EASE_OUT_EXPO, gsap, useGsapContext } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { RunControlDock } from "@/components/showcase/console/RunControlDock";
import { RunStatusPanel } from "@/components/showcase/console/RunStatusPanel";
import {
  INSTRUMENT_EYEBROW,
  INSTRUMENT_HEADLINE,
  INSTRUMENT_LEAD,
  INSTRUMENT_STEPS,
} from "@/components/showcase/copy";
import { LearningMatrix } from "@/components/showcase/console/LearningMatrix";

const sectionClass =
  "mx-auto w-full scroll-mt-24 px-6 py-24 md:px-12 md:py-32";

/**
 * Act III — the working heart. Presentational only: it receives the live session
 * + handlers from the page container and never fetches or holds run state.
 *
 * On ≥lg, console and evidence grid are separate GSAP-pinned beats: hold the run
 * controls first, release, then hold the matrix while verdicts stream in.
 */
export function ActInstrument({
  manifest,
  session,
  runErr,
  rollbackTarget,
  seriousUnlocked,
  startQuick,
  startSerious,
  cancelCurrentRun,
  approveCurrentRun,
  rejectCurrentRun,
  rollbackLatestRun,
}: {
  manifest: ShowcaseManifest | null;
  session: ShowcaseRunSession | null;
  runErr: string | null;
  rollbackTarget: ShowcaseRollbackTarget | null;
  seriousUnlocked: boolean;
  startQuick: () => void;
  startSerious: () => void;
  cancelCurrentRun: () => void;
  approveCurrentRun: () => void;
  rejectCurrentRun: () => void;
  rollbackLatestRun: () => void;
}) {
  const consoleRoot = useRef<HTMLElement>(null);
  const consolePin = useRef<HTMLDivElement>(null);
  const evidenceRoot = useRef<HTMLElement>(null);
  const evidencePin = useRef<HTMLDivElement>(null);

  useGsapContext(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1024px)", () => {
        gsap.timeline({
          scrollTrigger: {
            trigger: consoleRoot.current,
            start: "top 5rem",
            end: "+=75%",
            pin: consolePin.current,
            pinSpacing: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });
      });
      return () => mm.revert();
    },
    { scope: consoleRoot },
  );

  useGsapContext(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1024px)", () => {
        gsap.timeline({
          scrollTrigger: {
            trigger: evidenceRoot.current,
            start: "top 5rem",
            end: "+=100%",
            pin: evidencePin.current,
            pinSpacing: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });
      });
      return () => mm.revert();
    },
    { scope: evidenceRoot },
  );

  return (
    <>
      <section
        ref={consoleRoot}
        id="instrument"
        className={sectionClass}
        style={{ maxWidth: "var(--sc-container-max)" }}
      >
        <div ref={consolePin} className="flex flex-col gap-8">
          <motion.div
            className="flex flex-col gap-2"
            initial={{ opacity: 0, y: 14, filter: "blur(8px)" }}
            whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: true, amount: 0.6 }}
            transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
          >
            <MonoLabel>{INSTRUMENT_EYEBROW}</MonoLabel>
            <h2 className="sc-h2">{INSTRUMENT_HEADLINE}</h2>
            <InstrumentArc />
          </motion.div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.85fr_1.15fr]">
            <RunControlDock
              manifest={manifest}
              seriousUnlocked={seriousUnlocked}
              rollbackTarget={rollbackTarget}
              startQuick={startQuick}
              startSerious={startSerious}
              rollbackLatestRun={rollbackLatestRun}
            />
            <RunStatusPanel
              session={session}
              runErr={runErr}
              onCancel={cancelCurrentRun}
              onApprove={approveCurrentRun}
              onReject={rejectCurrentRun}
            />
          </div>
        </div>
      </section>

      <section
        ref={evidenceRoot}
        id="evidence-grid"
        className={`${sectionClass} pt-8 md:pt-16`}
        style={{ maxWidth: "var(--sc-container-max)" }}
      >
        <div ref={evidencePin} className="min-h-[70dvh] lg:min-h-[85dvh]">
          <LearningMatrix manifest={manifest} session={session} />
        </div>
      </section>
    </>
  );
}

function InstrumentArc() {
  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-prose sc-body">{INSTRUMENT_LEAD}</p>
      <ol className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {INSTRUMENT_STEPS.map((step, i) => (
          <li
            key={step.title}
            className="sc-panel-sunken flex list-none flex-col gap-1.5 rounded-md p-3.5"
          >
            <MonoLabel>{String(i + 1).padStart(2, "0")}</MonoLabel>
            <span className="sc-serif" style={{ fontSize: "0.98rem", color: "var(--sc-text)" }}>
              {step.title}
            </span>
            <span className="sc-body" style={{ fontSize: "0.85rem", color: "var(--sc-text-2)", lineHeight: 1.45 }}>
              {step.body}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
