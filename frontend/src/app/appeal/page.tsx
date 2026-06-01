"use client";
import { useEffect, useReducer, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { flowReducer, initialFlow, type FlowStep } from "@/lib/flow/reducer";
import { getDataSource } from "@/lib/data";
import type { AppealRequest, CaseSummary } from "@/lib/types";
import { Nav } from "@/components/Nav";
import { ProgressHairline } from "@/components/ui/ProgressHairline";
import { IntakePanel } from "@/components/flow/IntakePanel";
import { WorkingProgress } from "@/components/flow/WorkingProgress";
import { MirrorCard } from "@/components/flow/MirrorCard";
import { DraftEditor } from "@/components/flow/DraftEditor";
import { DecideBar } from "@/components/flow/DecideBar";

const STEP_RATIO: Record<FlowStep, number> = {
  intake: 0.1,
  working: 0.35,
  mirror: 0.6,
  draft: 0.85,
  decide: 1,
};

export default function AppealPage() {
  const [state, dispatch] = useReducer(flowReducer, initialFlow);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const reduced = useReducedMotion();
  const ds = getDataSource();

  useEffect(() => {
    ds.listCases().then(setCases);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(req: AppealRequest) {
    dispatch({ type: "SUBMIT", req });
    try {
      dispatch({ type: "RESULT", result: await ds.draftAppeal(req) });
    } catch {
      dispatch({ type: "ERROR", error: "Something's not working on our side. Try again, or come back later." });
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-surface-primary text-text-primary">
      <Nav />
      <div className="mt-8">
        <ProgressHairline ratio={STEP_RATIO[state.step]} />
      </div>
      <main className="mx-auto w-full max-w-(--container-prose) flex-1 px-6 py-16 md:px-12 md:py-24">
        {state.error && (
          <p className="mb-6 font-body text-sm text-status-error">{state.error}</p>
        )}
        <AnimatePresence mode="wait">
          <motion.div
            key={state.step}
            initial={reduced ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduced ? undefined : { opacity: 0, y: -8 }}
            transition={{ duration: 0.4, ease: [0.2, 0.8, 0.2, 1] }}
          >
            {state.step === "intake" && <IntakePanel cases={cases} onSubmit={submit} />}
            {state.step === "working" && <WorkingProgress />}
            {state.step === "mirror" && state.result && (
              <MirrorCard mirror={state.result.mirror} onContinue={() => dispatch({ type: "ADVANCE" })} />
            )}
            {state.step === "draft" && state.result && (
              <DraftEditor
                result={state.result}
                onEdit={(l) => dispatch({ type: "EDIT_LETTER", letter: l })}
                onContinue={() => dispatch({ type: "ADVANCE" })}
              />
            )}
            {state.step === "decide" && state.result && (
              <DecideBar result={state.result} onRestart={() => dispatch({ type: "RESET" })} />
            )}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
