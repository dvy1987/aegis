"use client";
import { useEffect, useMemo, useState } from "react";
import { showcaseSource } from "@/lib/data";
import {
  approveRun,
  cancelRun,
  getDemoState,
  getRollbackTarget,
  getRunSession,
  resolveShowcaseManifest,
  rejectRun,
  resumeRun,
  rollbackRun,
  startQuickRun,
  startSeriousRun,
} from "@/lib/data/live";
import { measuredLiftFromPersisted } from "@/lib/showcase/measuredLift";
import type {
  CaseSummary,
  MeasuredLiftCache,
  ShowcaseBundle,
  ShowcaseManifest,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import { Nav } from "@/components/Nav";
import { ShowcaseFilm } from "@/components/showcase/ShowcaseFilm";

const DEFAULT_CASE = "case_168_aetna_priorauth";
const TERMINAL = new Set([
  "successful",
  "failed",
  "cancelled",
  "rejected",
  "needs_approval",
  "rolled_back",
]);

function isRunning(session: ShowcaseRunSession | null): boolean {
  return Boolean(session && !TERMINAL.has(session.status));
}

export default function ShowcasePage() {
  const ds = showcaseSource;
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [sel, setSel] = useState(DEFAULT_CASE);
  const [bundle, setBundle] = useState<ShowcaseBundle | null>(null);
  const [manifest, setManifest] = useState<ShowcaseManifest | null>(null);
  const [previewSession, setPreviewSession] = useState<ShowcaseRunSession | null>(null);
  const [productionSession, setProductionSession] = useState<ShowcaseRunSession | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [measuredLift, setMeasuredLift] = useState<MeasuredLiftCache>({});
  const [rollbackTarget, setRollbackTarget] = useState<ShowcaseRollbackTarget | null>(null);
  const [runErr, setRunErr] = useState<string | null>(null);
  const [manifestWarning, setManifestWarning] = useState<string | null>(null);

  const activeSession = useMemo(() => {
    if (!activeSessionId) return null;
    if (previewSession?.session_id === activeSessionId) return previewSession;
    if (productionSession?.session_id === activeSessionId) return productionSession;
    return null;
  }, [activeSessionId, previewSession, productionSession]);

  const displaySession = activeSession ?? previewSession ?? productionSession;

  useEffect(() => {
    ds.listCases().then(setCases);
    resolveShowcaseManifest()
      .then(({ manifest: loaded, legacyApiWarning }) => {
        setManifest(loaded);
        setManifestWarning(legacyApiWarning);
      })
      .catch(() => undefined);
    getRollbackTarget().then(setRollbackTarget).catch(() => undefined);
    getDemoState()
      .then((state) => {
        if (state.preview_session) setPreviewSession(state.preview_session);
        if (state.production_session) setProductionSession(state.production_session);
        setMeasuredLift(measuredLiftFromPersisted(state.measured_lift));
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    ds.getShowcase(sel).then(setBundle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel]);

  useEffect(() => {
    if (!activeSessionId || !isRunning(activeSession)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getRunSession(activeSessionId);
        if (next.run_type === "quick") setPreviewSession(next);
        else setProductionSession(next);
        if (!isRunning(next)) setActiveSessionId(null);
      } catch (e) {
        setRunErr(e instanceof Error ? e.message : String(e));
      }
    }, 10000);
    return () => window.clearInterval(timer);
  }, [activeSessionId, activeSession]);

  useEffect(() => {
    const terminal = previewSession?.status === "successful" || productionSession?.status === "successful";
    if (!terminal) return;
    getRollbackTarget().then(setRollbackTarget).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewSession?.status, productionSession?.status]);

  function trackSession(session: ShowcaseRunSession) {
    if (session.run_type === "quick") setPreviewSession(session);
    else setProductionSession(session);
    if (isRunning(session)) setActiveSessionId(session.session_id);
    else setActiveSessionId(null);
  }

  async function startQuick() {
    setRunErr(null);
    try {
      trackSession(await startQuickRun());
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function startSerious() {
    setRunErr(null);
    try {
      trackSession(await startSeriousRun());
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function cancelCurrentRun() {
    if (!activeSession) return;
    setRunErr(null);
    try {
      trackSession(await cancelRun(activeSession.session_id));
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function approveCurrentRun() {
    if (!activeSession) return;
    setRunErr(null);
    try {
      trackSession(await approveRun(activeSession.session_id));
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function rejectCurrentRun() {
    if (!activeSession) return;
    setRunErr(null);
    try {
      trackSession(await rejectRun(activeSession.session_id));
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function resumeCurrentRun() {
    if (!activeSession) return;
    setRunErr(null);
    try {
      trackSession(await resumeRun(activeSession.session_id));
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function rollbackLatestRun() {
    setRunErr(null);
    try {
      await rollbackRun();
      setRollbackTarget(await getRollbackTarget());
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  function onMeasuredLiftUpdate(caseId: string, variant: "baseline" | "candidate", result: import("@/lib/types").ShowcaseMeasureResult) {
    setMeasuredLift((prev) => ({
      ...prev,
      [caseId]: { ...prev[caseId], [variant]: result },
    }));
  }

  const seriousUnlocked = previewSession?.status === "successful";

  return (
    <div className="flex min-h-dvh flex-col">
      <Nav />
      <main className="flex-1">
        <ShowcaseFilm
          cases={cases}
          sel={sel}
          setSel={setSel}
          bundle={bundle}
          manifest={manifest}
          manifestWarning={manifestWarning}
          previewSession={previewSession}
          productionSession={productionSession}
          displaySession={displaySession}
          activeSession={activeSession}
          measuredLift={measuredLift}
          onMeasuredLiftUpdate={onMeasuredLiftUpdate}
          rollbackTarget={rollbackTarget}
          runErr={runErr}
          seriousUnlocked={seriousUnlocked}
          startQuick={startQuick}
          startSerious={startSerious}
          cancelCurrentRun={cancelCurrentRun}
          resumeCurrentRun={resumeCurrentRun}
          approveCurrentRun={approveCurrentRun}
          rejectCurrentRun={rejectCurrentRun}
          rollbackLatestRun={rollbackLatestRun}
        />
      </main>
    </div>
  );
}
