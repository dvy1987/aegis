"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { ShowcaseRunSession } from "@/lib/types";
import { EASE_OUT_EXPO, statusMorph } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";
import { StatusOrb } from "@/components/showcase/fx/StatusOrb";

const STAGE_CAPTIONS: Record<string, string> = {
  queued: "Queued — work starts on the server.",
  measure_before: "Measuring held-out cases with the current prompt — no learning yet.",
  train_gepa: "Drafting, judging, and running the optimizer on training cases.",
  waiting_for_approval: "Proposed changes ready — you decide whether to ship them.",
  promote: "Promoting the approved changes.",
  measure_after: "Re-measuring held-out cases with the promoted prompt.",
  failed: "The run stopped. See the error below.",
  cancelled: "Run cancelled. No promotion happened.",
  rejected: "Proposal discarded. Nothing was promoted.",
  rolled_back: "Previous prompt and playbook restored.",
};

const TERMINAL = ["successful", "failed", "cancelled", "rejected", "rolled_back"];

export function RunStatusPanel({
  session,
  runErr,
  onCancel,
  onApprove,
  onReject,
}: {
  session: ShowcaseRunSession | null;
  runErr?: string | null;
  onCancel: () => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  if (!session) return <StandbyConsole runErr={runErr} />;

  const { diagnostics, status } = session;
  const total = diagnostics.total_cases;
  const done = diagnostics.completed_cases;
  const pct = total ? Math.round((done / total) * 100) : 0;
  const stage = diagnostics.stage;
  const needsApproval = status === "needs_approval";
  const canCancel = !TERMINAL.includes(status);

  return (
    <GlassPanel variant={needsApproval ? "active" : "default"} className="flex flex-col gap-5 p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <MonoLabel>Run status</MonoLabel>
          <span className="break-all sc-mono" style={{ color: "var(--sc-text-2)" }}>
            {session.session_id}
          </span>
        </div>
        <StatusOrb status={status} />
      </div>

      <div>
        <AnimatePresence mode="wait">
          <motion.h3
            key={stage}
            variants={statusMorph}
            initial="initial"
            animate="animate"
            exit="exit"
            className="sc-h2"
            style={{ fontSize: "1.75rem" }}
          >
            {stage.replaceAll("_", " ")}
          </motion.h3>
        </AnimatePresence>
        <p className="mt-2 sc-body" style={{ fontSize: "0.95rem", color: "var(--sc-text-2)" }}>
          {STAGE_CAPTIONS[stage] ?? " "}
        </p>
      </div>

      <ProgressBar done={done} total={total} pct={pct} />

      {diagnostics.last_error && (
        <div
          className="rounded-md p-3"
          style={{ border: "1px solid var(--sc-deny)", background: "color-mix(in oklch, var(--sc-deny) 12%, transparent)" }}
        >
          <p className="sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text)" }}>
            {diagnostics.last_error.message}
          </p>
          <p className="mt-1 sc-mono">{diagnostics.last_error.code}</p>
        </div>
      )}

      {session.regression_detected && session.regression_summary && (
        <motion.div
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, ease: EASE_OUT_EXPO }}
          className="rounded-md p-3"
          style={{ border: "1px solid var(--sc-warn)", background: "color-mix(in oklch, var(--sc-warn) 12%, transparent)" }}
        >
          <p className="sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text)" }}>
            {session.regression_summary}
          </p>
        </motion.div>
      )}

      {runErr && (
        <p className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-2)" }}>
          {runErr}
        </p>
      )}

      {diagnostics.cloud_log_filter && (
        <p className="break-all sc-mono">Log filter: {diagnostics.cloud_log_filter}</p>
      )}

      <div className="flex flex-wrap gap-3">
        <AnimatePresence>
          {needsApproval && (
            <motion.div
              key="approval"
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.5, ease: EASE_OUT_EXPO }}
              className="flex flex-wrap gap-3"
            >
              <IgniteButton variant="primary" onClick={onApprove}>
                Approve update
              </IgniteButton>
              <IgniteButton variant="secondary" onClick={onReject}>
                Reject update
              </IgniteButton>
            </motion.div>
          )}
        </AnimatePresence>
        {canCancel && (
          <IgniteButton variant="ghost" onClick={onCancel}>
            Cancel run
          </IgniteButton>
        )}
      </div>
    </GlassPanel>
  );
}

function ProgressBar({ done, total, pct }: { done: number; total: number; pct: number }) {
  const reduce = useReducedMotion();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="sc-mono" style={{ color: "var(--sc-text-2)" }}>
          {done} / {total || "—"} cases
        </span>
        <span className="sc-mono">{total ? `${pct}%` : ""}</span>
      </div>
      <div className="h-px w-full overflow-hidden" style={{ background: "var(--sc-hairline)" }}>
        <motion.div
          className="h-px"
          style={{ background: "var(--sc-accent)", boxShadow: "0 0 8px var(--sc-accent-glow)" }}
          initial={false}
          animate={{ width: `${total ? pct : 0}%` }}
          transition={reduce ? { duration: 0 } : { duration: 0.6, ease: EASE_OUT_EXPO }}
        />
      </div>
    </div>
  );
}

function StandbyConsole({ runErr }: { runErr?: string | null }) {
  return (
    <GlassPanel className="flex min-h-72 flex-col justify-between gap-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <MonoLabel>Run status</MonoLabel>
          <span className="sc-mono sc-blink" style={{ color: "var(--sc-text-2)" }}>
            AWAITING SESSION
          </span>
        </div>
        <StatusOrb status={null} />
      </div>

      {/* dim matrix outline */}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(1.1rem,1fr))] gap-1" aria-hidden>
        {Array.from({ length: 36 }).map((_, i) => (
          <span key={i} className="sc-cell sc-cell--pending sc-pulse-soft" style={{ animationDelay: `${(i % 12) * 0.12}s` }} />
        ))}
      </div>

      <div className="flex items-center gap-3">
        <span className="h-2 w-2 rounded-full sc-pulse-soft" style={{ background: "var(--sc-accent)" }} />
        <p className="sc-body" style={{ fontSize: "0.95rem", color: "var(--sc-text-2)" }}>
          Begin a live run to watch the session id, stage, and evidence appear here.
        </p>
      </div>
      {runErr && (
        <p className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-2)" }}>
          {runErr}
        </p>
      )}
    </GlassPanel>
  );
}
