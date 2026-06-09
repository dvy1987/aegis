"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { ShowcaseManifest, ShowcaseRunSession } from "@/lib/types";
import { resolveInactiveStatusNarrative } from "./statusNarrative";
import { resolveStatusPreviewBatch } from "./statusPreviewBatch";
import { EASE_OUT_EXPO, statusMorph } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";
import {
  APPROVE_CTA,
  CANCEL_CTA,
  REJECT_CTA,
  STAGE_CAPTIONS,
  STATUS_AWAITING,
  STATUS_EYEBROW,
  STATUS_JUST_NOW_EYEBROW,
  STATUS_UP_NEXT_EYEBROW,
} from "@/components/showcase/copy";
import { StatusOrb } from "@/components/showcase/fx/StatusOrb";

const TERMINAL = ["successful", "failed", "cancelled", "rejected", "rolled_back"];

export function RunStatusPanel({
  manifest,
  session,
  seriousUnlocked,
  runErr,
  onCancel,
  onApprove,
  onReject,
}: {
  manifest: ShowcaseManifest | null;
  session: ShowcaseRunSession | null;
  seriousUnlocked: boolean;
  runErr?: string | null;
  onCancel: () => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  const preview = resolveStatusPreviewBatch(manifest, session, seriousUnlocked);

  if (!session) {
    return (
      <StandbyConsole
        manifest={manifest}
        seriousUnlocked={seriousUnlocked}
        preview={preview}
        runErr={runErr}
      />
    );
  }

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
          <MonoLabel>{STATUS_EYEBROW}</MonoLabel>
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

      <StatusPreviewGrid count={preview.count} verdicts={preview.verdicts} />

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
                {APPROVE_CTA}
              </IgniteButton>
              <IgniteButton variant="secondary" onClick={onReject}>
                {REJECT_CTA}
              </IgniteButton>
            </motion.div>
          )}
        </AnimatePresence>
        {canCancel && (
          <IgniteButton variant="ghost" onClick={onCancel}>
            {CANCEL_CTA}
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

function StatusPreviewGrid({ count, verdicts }: { count: number; verdicts: string[] }) {
  if (count === 0) return null;

  const compact = count <= 20;

  return (
    <div
      className={
        compact
          ? "inline-grid gap-1"
          : "grid max-h-36 grid-cols-[repeat(auto-fill,minmax(1.25rem,1fr))] gap-1 overflow-auto"
      }
      style={compact ? { gridTemplateColumns: `repeat(${count}, 1.25rem)` } : undefined}
      role="img"
      aria-label={`${count} case${count === 1 ? "" : "s"} in the next batch`}
    >
      {Array.from({ length: count }, (_, i) => {
        const verdict = verdicts[i];
        const tone =
          verdict === "APPROVE" ? "sc-cell--approve" : verdict === "DENY" ? "sc-cell--deny" : "sc-cell--pending";
        const pending = !verdict;
        return (
          <span
            key={i}
            className={`sc-cell block min-h-5 min-w-5 ${tone}${pending ? " sc-pulse-soft" : ""}`}
            style={pending ? { animationDelay: `${(i % 12) * 0.12}s` } : undefined}
          />
        );
      })}
    </div>
  );
}

function StandbyConsole({
  manifest,
  seriousUnlocked,
  preview,
  runErr,
}: {
  manifest: ShowcaseManifest | null;
  seriousUnlocked: boolean;
  preview: { count: number; verdicts: string[] };
  runErr?: string | null;
}) {
  const narrative = resolveInactiveStatusNarrative(manifest, seriousUnlocked);

  return (
    <GlassPanel className="flex min-h-72 flex-col gap-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <MonoLabel>{STATUS_EYEBROW}</MonoLabel>
          <span className="sc-mono sc-blink" style={{ color: "var(--sc-text-2)" }}>
            {STATUS_AWAITING}
          </span>
        </div>
        <StatusOrb status={null} />
      </div>

      <StatusPreviewGrid count={preview.count} verdicts={preview.verdicts} />

      <div className="grid gap-4">
        {narrative.justNow && (
          <div>
            <MonoLabel>{STATUS_JUST_NOW_EYEBROW}</MonoLabel>
            <p className="mt-1.5 sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text-2)", lineHeight: 1.5 }}>
              {narrative.justNow}
            </p>
          </div>
        )}
        <div>
          <MonoLabel>{STATUS_UP_NEXT_EYEBROW}</MonoLabel>
          <p className="mt-1.5 sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text)", lineHeight: 1.5 }}>
            {narrative.upNext}
          </p>
        </div>
      </div>

      {runErr && (
        <p className="sc-body" style={{ fontSize: "0.875rem", color: "var(--sc-text-2)" }}>
          {runErr}
        </p>
      )}
    </GlassPanel>
  );
}
