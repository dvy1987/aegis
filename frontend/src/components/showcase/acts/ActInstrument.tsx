"use client";

import { motion } from "framer-motion";
import type {
  ShowcaseManifest,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { RunControlDock } from "@/components/showcase/console/RunControlDock";
import { RunStatusPanel } from "@/components/showcase/console/RunStatusPanel";
import { LearningMatrix } from "@/components/showcase/console/LearningMatrix";

/**
 * Act III — the working heart. Presentational only: it receives the live session
 * + handlers from the page container and never fetches or holds run state.
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
  return (
    <section
      id="instrument"
      className="mx-auto w-full scroll-mt-24 px-6 py-24 md:px-12 md:py-32"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <motion.div
        className="mb-10 flex flex-col gap-2"
        initial={{ opacity: 0, y: 14, filter: "blur(8px)" }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, amount: 0.6 }}
        transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
      >
        <MonoLabel>The live instrument</MonoLabel>
        <h2 className="sc-h2">Watch it run, and make the call.</h2>
        <p className="max-w-prose sc-body">
          Start a learning check. The UI returns immediately while work continues on the server — it
          pauses for your approval before anything ships.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.85fr_1.15fr]">
        <div className="lg:sticky lg:top-24 lg:self-start">
          <RunControlDock
            manifest={manifest}
            seriousUnlocked={seriousUnlocked}
            rollbackTarget={rollbackTarget}
            startQuick={startQuick}
            startSerious={startSerious}
            rollbackLatestRun={rollbackLatestRun}
          />
        </div>
        <RunStatusPanel
          session={session}
          runErr={runErr}
          onCancel={cancelCurrentRun}
          onApprove={approveCurrentRun}
          onReject={rejectCurrentRun}
        />
      </div>

      <div className="mt-8">
        <LearningMatrix manifest={manifest} session={session} />
      </div>
    </section>
  );
}
