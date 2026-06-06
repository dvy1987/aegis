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
import { CasePicker } from "@/components/showcase/CasePicker";
import { VersusPanel } from "@/components/showcase/VersusPanel";
import { DiffCard } from "@/components/showcase/DiffCard";
import { CounterfactualCard } from "@/components/showcase/CounterfactualCard";
import { ArrowUpRightIcon } from "@/icons";
import { Button } from "@/components/Button";

const DEFAULT_CASE = "case_13_cigna_mednec";

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
    }, 3000);
    return () => window.clearInterval(timer);
  }, [runSession]);

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
      setRunSession(await approveRun(runSession.session_id));
      setRollbackTarget(await getRollbackTarget());
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
    <div className="flex min-h-dvh flex-col bg-surface-primary text-text-primary">
      <Nav />
      <main className="mx-auto flex w-full max-w-(--container-app) flex-1 flex-col gap-16 px-6 py-16 md:px-12 md:py-24">
        <header className="flex flex-col gap-4">
          <p className="inline-flex items-center gap-2 font-body text-sm text-text-secondary">
            <span aria-hidden className="signature-dot" />
            How Aegis learns
          </p>
          <h1 className="max-w-3xl font-display text-display-lg font-semibold leading-[1.1] tracking-tight md:text-display-xl">
            This tool improves from its own observability.
          </h1>
          <p className="max-w-prose font-body text-lg text-text-secondary">
            Pick a case. The same denial is drafted by an earlier version and an improved one, scored
            on a held-out benchmark. The improvement comes from the system reading its own past
            evaluations — not from hand-tuning.
          </p>
        </header>

        <CasePicker cases={cases} selected={sel} onSelect={setSel} />

        <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="flex flex-col gap-4">
            <div className="flex flex-col gap-4">
              <div>
                <p className="font-body text-sm text-text-tertiary">Current mode</p>
                <h2 className="font-display text-2xl font-semibold">Human-approved learning</h2>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-border-subtle bg-surface-primary p-4">
                  <p className="font-body text-sm text-text-tertiary">Quick learning check</p>
                  <p className="mt-2 font-body text-sm text-text-secondary">
                    {manifest ? `${manifest.quick_train.length} train + ${manifest.quick_holdout.length} holdout ${manifest.quick_slice.replace("_", " ")} cases` : "Targeted quick set"}
                  </p>
                  <Button className="mt-4 h-10 px-4 text-sm" onClick={startQuick}>
                    Run quick check
                  </Button>
                </div>
                <div className="rounded-md border border-border-subtle bg-surface-primary p-4">
                  <p className="font-body text-sm text-text-tertiary">Serious learning pass</p>
                  <p className="mt-2 font-body text-sm text-text-secondary">
                    Locked until the quick check succeeds.
                  </p>
                  <Button
                    className="mt-4 h-10 px-4 text-sm"
                    variant="secondary"
                    onClick={startSerious}
                    disabled={!seriousUnlocked}
                  >
                    Run serious pass
                  </Button>
                  {rollbackTarget && (
                    <Button className="mt-3 h-10 px-4 text-sm" variant="ghost" onClick={rollbackLatestRun}>
                      Roll back latest update
                    </Button>
                  )}
                </div>
              </div>
              {runErr && <p className="font-body text-sm text-text-secondary">{runErr}</p>}
            </div>
          </section>

          <section className="rounded-lg border border-border-subtle bg-surface-secondary p-5">
            <RunStatusPanel
              session={runSession}
              onCancel={cancelCurrentRun}
              onApprove={approveCurrentRun}
              onReject={rejectCurrentRun}
            />
          </section>
        </div>

        <LearningMatrix manifest={manifest} session={runSession} />

        {bundle && (
          <>
            <VersusPanel bundle={bundle} />
            <DiffCard whatChanged={bundle.what_changed} />
            <CounterfactualCard on={bundle.counterfactual.on_composite} off={bundle.counterfactual.off_composite} />
            {bundle.phoenix_url && (
              <a
                href={bundle.phoenix_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 font-body text-base text-text-link hover:text-text-primary"
              >
                Open the underlying trace
                <ArrowUpRightIcon size={16} />
              </a>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function RunStatusPanel({
  session,
  onCancel,
  onApprove,
  onReject,
}: {
  session: ShowcaseRunSession | null;
  onCancel: () => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  if (!session) {
    return (
      <div className="flex min-h-48 flex-col justify-between">
        <div>
          <p className="font-body text-sm text-text-tertiary">Run status</p>
          <h2 className="mt-2 font-display text-2xl font-semibold">No live run started</h2>
        </div>
        <p className="font-body text-sm text-text-secondary">
          Start a run to see the session id, current stage, and troubleshooting details.
        </p>
      </div>
    );
  }
  const pct = session.diagnostics.total_cases
    ? Math.round((session.diagnostics.completed_cases / session.diagnostics.total_cases) * 100)
    : 0;
  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="font-body text-sm text-text-tertiary">Session id</p>
        <p className="mt-1 break-all font-body text-sm text-text-primary">{session.session_id}</p>
      </div>
      <div>
        <p className="font-body text-sm text-text-tertiary">Current stage</p>
        <h2 className="mt-1 font-display text-2xl font-semibold">
          {session.diagnostics.stage.replaceAll("_", " ")}
        </h2>
        <p className="mt-2 font-body text-sm text-text-secondary">
          {session.diagnostics.completed_cases} of {session.diagnostics.total_cases} cases complete
          {pct ? ` (${pct}%)` : ""}
        </p>
      </div>
      {session.diagnostics.last_error && (
        <div className="rounded-md border border-border-subtle bg-surface-primary p-3">
          <p className="font-body text-sm font-medium text-text-primary">{session.diagnostics.last_error.message}</p>
          <p className="mt-1 font-body text-xs text-text-tertiary">{session.diagnostics.last_error.code}</p>
        </div>
      )}
      {session.regression_detected && session.regression_summary && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3">
          <p className="font-body text-sm font-medium text-amber-950">{session.regression_summary}</p>
        </div>
      )}
      {session.diagnostics.cloud_log_filter && (
        <p className="break-all font-body text-xs text-text-tertiary">
          Log filter: {session.diagnostics.cloud_log_filter}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        {session.status === "needs_approval" && (
          <Button className="h-10 px-4 text-sm" onClick={onApprove}>
            Approve update
          </Button>
        )}
        {session.status === "needs_approval" && (
          <Button className="h-10 px-4 text-sm" variant="secondary" onClick={onReject}>
            Reject update
          </Button>
        )}
        {!["successful", "failed", "cancelled", "rejected", "rolled_back"].includes(session.status) && (
          <Button className="h-10 px-4 text-sm" variant="secondary" onClick={onCancel}>
            Cancel run
          </Button>
        )}
      </div>
    </div>
  );
}

function LearningMatrix({
  manifest,
  session,
}: {
  manifest: ShowcaseManifest | null;
  session: ShowcaseRunSession | null;
}) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <RunColumn
        title="Demo"
        subtitle={manifest ? `${manifest.quick_train.length} train · ${manifest.quick_holdout.length} holdout` : "Quick check"}
        session={session?.run_type === "quick" ? session : null}
        lockedMessage="Run quick check to populate this view."
      />
      <RunColumn
        title="Serious"
        subtitle={manifest ? `${manifest.serious_train_count} train · ${manifest.serious_holdout.length} holdout` : "Serious pass"}
        session={session?.run_type === "serious" ? session : null}
        lockedMessage="Locked until the quick check succeeds."
      />
    </section>
  );
}

function RunColumn({
  title,
  subtitle,
  session,
  lockedMessage,
}: {
  title: string;
  subtitle: string;
  session: ShowcaseRunSession | null;
  lockedMessage: string;
}) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-secondary p-4">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold">{title}</h2>
          <p className="mt-1 font-body text-sm text-text-secondary">{subtitle}</p>
        </div>
        {session && (
          <span className="rounded-sm border border-border-subtle bg-surface-primary px-2 py-1 font-body text-xs text-text-secondary">
            {session.status.replaceAll("_", " ")}
          </span>
        )}
      </div>
      <div className="grid gap-3">
        <StageBox
          title="Pre-training"
          results={session?.pre_measure_results ?? []}
          emptyMessage={session ? "Waiting for held-out measurement." : lockedMessage}
        />
        <TrainingBox
          before={session?.training_pre_measure_results ?? []}
          after={session?.training_post_measure_results ?? []}
          emptyMessage={session ? "Waiting for training measurements." : lockedMessage}
        />
        <StageBox
          title="Post-training"
          results={session?.post_measure_results ?? []}
          emptyMessage={session ? "Waiting for approval." : lockedMessage}
        />
      </div>
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
    <div className="rounded-md border border-border-subtle bg-surface-primary p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="font-body text-sm font-medium text-text-primary">Training</h3>
        {hasData && <p className="font-body text-xs text-text-tertiary">before / after</p>}
      </div>
      {hasData ? (
        <div className="grid gap-2">
          <OutcomeGrid results={before} rowLabel="Before" />
          <OutcomeGrid results={after} rowLabel="After" />
        </div>
      ) : (
        <p className="font-body text-sm text-text-tertiary">{emptyMessage}</p>
      )}
    </div>
  );
}

function StageBox({
  title,
  results,
  emptyMessage,
}: {
  title: string;
  results: Record<string, unknown>[];
  emptyMessage: string;
}) {
  return (
    <div className="rounded-md border border-border-subtle bg-surface-primary p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="font-body text-sm font-medium text-text-primary">{title}</h3>
        {results.length > 0 && <p className="font-body text-xs text-text-tertiary">{results.length} cases</p>}
      </div>
      {results.length > 0 ? (
        <OutcomeGrid results={results} />
      ) : (
        <p className="font-body text-sm text-text-tertiary">{emptyMessage}</p>
      )}
    </div>
  );
}

function OutcomeGrid({
  results,
  rowLabel,
}: {
  results: Record<string, unknown>[];
  rowLabel?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      {rowLabel && <span className="w-12 shrink-0 font-body text-xs text-text-tertiary">{rowLabel}</span>}
      <div className="grid max-h-36 flex-1 grid-cols-[repeat(auto-fill,minmax(1.25rem,1fr))] gap-1 overflow-auto">
        {results.map((result, index) => {
          const verdict = String(result.verdict ?? "").toUpperCase();
          const approved = verdict === "APPROVE";
          const caseId = String(result.case_id ?? `case_${index + 1}`);
          return (
            <span
              key={`${caseId}-${index}`}
              title={`${caseId}: ${verdict || "pending"}`}
              className={[
                "block aspect-square min-w-5 rounded-sm border",
                approved
                  ? "border-emerald-700 bg-emerald-500"
                  : "border-rose-800 bg-rose-500",
              ].join(" ")}
            />
          );
        })}
      </div>
    </div>
  );
}
