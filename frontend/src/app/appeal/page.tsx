"use client";
import { useEffect, useReducer, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { flowReducer, initialFlow, type FlowStep } from "@/lib/flow/reducer";
import {
  clearAppealSession,
  loadAppealSession,
  saveAppealSession,
  type PersistedAppealSession,
} from "@/lib/flow/persistAppealSession";
import { consumerSource } from "@/lib/data";
import type { AppealRequest, CaseSummary } from "@/lib/types";
import { getDiscoveryEnabled, SETTINGS_CHANGED_EVENT } from "@/lib/settings";
import { Nav } from "@/components/Nav";
import { ProgressHairline } from "@/components/ui/ProgressHairline";
import { IntakePanel } from "@/components/flow/IntakePanel";
import { QuestionChat } from "@/components/flow/QuestionChat";
import { WorkingProgress } from "@/components/flow/WorkingProgress";
import { MirrorCard } from "@/components/flow/MirrorCard";
import { ResumeAppealBanner } from "@/components/flow/ResumeAppealBanner";
import { DraftEditor } from "@/components/flow/DraftEditor";
import { DecideBar } from "@/components/flow/DecideBar";
import { cn } from "@/lib/cn";

const STEP_LABELS: Record<FlowStep, string> = {
  intake: "start",
  questions: "questions",
  working: "drafting",
  mirror: "summary",
  draft: "draft review",
  decide: "finish",
};

const STEP_RATIO: Record<FlowStep, number> = {
  intake: 0.1,
  questions: 0.25,
  working: 0.45,
  mirror: 0.65,
  draft: 0.85,
  decide: 1,
};

export default function AppealPage() {
  const [state, dispatch] = useReducer(flowReducer, initialFlow);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [settingsTick, setSettingsTick] = useState(0);
  const reduced = useReducedMotion();
  const ds = consumerSource;

  useEffect(() => {
    ds.listCases().then(setCases);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settingsTick]);

  useEffect(() => {
    const onSettings = () => setSettingsTick((n) => n + 1);
    window.addEventListener(SETTINGS_CHANGED_EVENT, onSettings);
    return () => window.removeEventListener(SETTINGS_CHANGED_EVENT, onSettings);
  }, []);

  function submit(req: AppealRequest) {
    // The questions step runs between intake and drafting (traced, not graded).
    dispatch({
      type: "BEGIN_QUESTIONS",
      req: { ...req, discovery_enabled: getDiscoveryEnabled() },
    });
  }

  async function draft(baseReq: AppealRequest, interviewId?: string) {
    const req: AppealRequest = { ...baseReq, interview_id: interviewId };
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
      <main
        className={cn(
          "mx-auto w-full flex-1 px-6 py-16 md:px-12 md:py-24",
          state.step === "intake" ? "max-w-(--container-wide)" : "max-w-(--container-prose)",
        )}
      >
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
            {state.step === "questions" && state.req && (
              <QuestionChat
                req={state.req}
                source={ds}
                onFinish={(interviewId) => void draft(state.req as AppealRequest, interviewId)}
              />
            )}
            {state.step === "working" && <WorkingProgress />}
            {state.step === "mirror" && state.result && (
              <MirrorCard
                mirror={state.result.mirror}
                additionalDetails={state.additionalDetails ?? ""}
                onSaveDetails={(text) => dispatch({ type: "ADD_DETAILS", text })}
                onContinue={() => dispatch({ type: "ADVANCE" })}
              />
            )}
            {state.step === "draft" && state.result && state.req && (
              <DraftEditor
                req={state.req}
                result={state.result}
                additionalDetails={state.additionalDetails}
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
