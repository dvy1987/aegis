"use client";
import { useEffect, useState } from "react";
import { showcaseSource } from "@/lib/data";
import {
  approveRun,
  cancelRun,
  getRollbackTarget,
  getRunSession,
  getShowcaseManifest,
  rejectRun,
  rollbackRun,
  startQuickRun,
  startSeriousRun,
} from "@/lib/data/live";
import type {
  CaseSummary,
  ShowcaseBundle,
  ShowcaseManifest,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import { Nav } from "@/components/Nav";
import { ShowcaseFilm } from "@/components/showcase/ShowcaseFilm";

const DEFAULT_CASE = "case_126_cigna_mednec";

export default function ShowcasePage() {
  const ds = showcaseSource;
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [sel, setSel] = useState(DEFAULT_CASE);
  const [bundle, setBundle] = useState<ShowcaseBundle | null>(null);
  const [manifest, setManifest] = useState<ShowcaseManifest | null>(null);
  const [runSession, setRunSession] = useState<ShowcaseRunSession | null>(null);
  const [rollbackTarget, setRollbackTarget] = useState<ShowcaseRollbackTarget | null>(null);
  const [runErr, setRunErr] = useState<string | null>(null);

  useEffect(() => {
    ds.listCases().then(setCases);
    getShowcaseManifest().then(setManifest).catch(() => undefined);
    getRollbackTarget().then(setRollbackTarget).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    ds.getShowcase(sel).then(setBundle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel]);

  useEffect(() => {
    if (!runSession) return;
    if (["successful", "failed", "cancelled", "rejected", "needs_approval", "rolled_back"].includes(runSession.status)) return;
    const timer = window.setInterval(async () => {
      try {
        setRunSession(await getRunSession(runSession.session_id));
      } catch (e) {
        setRunErr(e instanceof Error ? e.message : String(e));
      }
    }, 10000);
    return () => window.clearInterval(timer);
  }, [runSession]);

  // Promotion now happens in the background after approval, so refresh the
  // rollback target once the run reaches a state where it may have changed.
  useEffect(() => {
    if (!runSession) return;
    if (!["successful", "rolled_back"].includes(runSession.status)) return;
    getRollbackTarget().then(setRollbackTarget).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runSession?.status]);

  async function startQuick() {
    setRunErr(null);
    try {
      setRunSession(await startQuickRun());
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function startSerious() {
    setRunErr(null);
    try {
      setRunSession(await startSeriousRun());
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function cancelCurrentRun() {
    if (!runSession) return;
    setRunErr(null);
    try {
      setRunSession(await cancelRun(runSession.session_id));
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function approveCurrentRun() {
    if (!runSession) return;
    setRunErr(null);
    try {
      // Approval returns immediately with a running status; the polling effect
      // tracks promotion + post-measure to completion, then refreshes rollback.
      setRunSession(await approveRun(runSession.session_id));
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function rejectCurrentRun() {
    if (!runSession) return;
    setRunErr(null);
    try {
      setRunSession(await rejectRun(runSession.session_id));
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

  const seriousUnlocked = runSession?.run_type === "quick" && runSession.status === "successful";

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
          runSession={runSession}
          rollbackTarget={rollbackTarget}
          runErr={runErr}
          seriousUnlocked={seriousUnlocked}
          startQuick={startQuick}
          startSerious={startSerious}
          cancelCurrentRun={cancelCurrentRun}
          approveCurrentRun={approveCurrentRun}
          rejectCurrentRun={rejectCurrentRun}
          rollbackLatestRun={rollbackLatestRun}
        />
      </main>
    </div>
  );
}
