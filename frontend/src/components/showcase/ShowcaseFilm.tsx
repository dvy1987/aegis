"use client";

import { useEffect } from "react";
import { MotionConfig, motion, useReducedMotion, useScroll } from "framer-motion";
import type {
  CaseSummary,
  ShowcaseBundle,
  ShowcaseManifest,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import { ScrollTrigger, TheatricalProvider, useTheatrical } from "@/lib/motion";
import { ActHero } from "@/components/showcase/acts/ActHero";
import { ActThesis } from "@/components/showcase/acts/ActThesis";
import { ActInstrument } from "@/components/showcase/acts/ActInstrument";
import { ActBeforeAfter } from "@/components/showcase/acts/ActBeforeAfter";
import { ActIntelligence } from "@/components/showcase/acts/ActIntelligence";
import { ActImpact } from "@/components/showcase/acts/ActImpact";
import { StatusHUD } from "@/components/showcase/console/StatusHUD";

export interface ShowcaseFilmProps {
  cases: CaseSummary[];
  sel: string;
  setSel: (id: string) => void;
  bundle: ShowcaseBundle | null;
  manifest: ShowcaseManifest | null;
  runSession: ShowcaseRunSession | null;
  rollbackTarget: ShowcaseRollbackTarget | null;
  runErr: string | null;
  seriousUnlocked: boolean;
  startQuick: () => void;
  startSerious: () => void;
  cancelCurrentRun: () => void;
  resumeCurrentRun: () => void;
  approveCurrentRun: () => void;
  rejectCurrentRun: () => void;
  rollbackLatestRun: () => void;
}

/**
 * Layout spine: orders the six Acts and owns the scroll-progress line. All run
 * state lives in the page container and flows down as props (logic preserved).
 */
export function ShowcaseFilm(props: ShowcaseFilmProps) {
  return (
    <MotionConfig reducedMotion="user">
      <TheatricalProvider>
        <ShowcaseFilmBody {...props} />
      </TheatricalProvider>
    </MotionConfig>
  );
}

function ShowcaseFilmBody(props: ShowcaseFilmProps) {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const { active } = useTheatrical();

  useEffect(() => {
    if (reduce) return;
    const refresh = () => ScrollTrigger.refresh();
    refresh();
    window.addEventListener("load", refresh);
    window.addEventListener("resize", refresh);
    return () => {
      window.removeEventListener("load", refresh);
      window.removeEventListener("resize", refresh);
    };
  }, [reduce]);

  return (
    <div className={active ? "sc-theatrical-busy" : undefined} data-theatrical={active ?? undefined}>
      {!reduce && (
        <motion.div
          className="sc-scroll-progress"
          style={{ width: "100%", scaleX: scrollYProgress }}
          aria-hidden
        />
      )}
      <StatusHUD session={props.runSession} />

      <ActHero />
      <ActThesis />
      <ActInstrument
        manifest={props.manifest}
        session={props.runSession}
        runErr={props.runErr}
        rollbackTarget={props.rollbackTarget}
        seriousUnlocked={props.seriousUnlocked}
        startQuick={props.startQuick}
        startSerious={props.startSerious}
        cancelCurrentRun={props.cancelCurrentRun}
        resumeCurrentRun={props.resumeCurrentRun}
        approveCurrentRun={props.approveCurrentRun}
        rejectCurrentRun={props.rejectCurrentRun}
        rollbackLatestRun={props.rollbackLatestRun}
      />
      <ActBeforeAfter
        bundle={props.bundle}
        cases={props.cases}
        selected={props.sel}
        onSelect={props.setSel}
      />
      <ActIntelligence
        on={props.bundle?.counterfactual.on_composite ?? 0}
        off={props.bundle?.counterfactual.off_composite ?? 0}
      />
      <ActImpact />
    </div>
  );
}
