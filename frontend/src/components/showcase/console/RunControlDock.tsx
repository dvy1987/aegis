"use client";

import type { ReactNode } from "react";
import type { ShowcaseManifest, ShowcaseRollbackTarget } from "@/lib/types";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import {
  DOCK_EYEBROW,
  DOCK_HEADLINE,
  DOCK_QUICK_CTA,
  DOCK_QUICK_TITLE,
  DOCK_ROLLBACK,
  DOCK_SERIOUS_CTA,
  DOCK_RUNS_DISABLED,
  DOCK_RUNS_DISABLED_TOOLTIP,
  DOCK_SERIOUS_LOCKED,
  DOCK_SERIOUS_TITLE,
} from "@/components/showcase/copy";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";

/** Native title on a wrapper — disabled buttons do not emit hover events themselves. */
function BlockedActionTooltip({ show, children }: { show: boolean; children: ReactNode }) {
  if (!show) return <>{children}</>;
  return (
    <span className="block w-full" title={DOCK_RUNS_DISABLED_TOOLTIP}>
      {children}
    </span>
  );
}

/**
 * The floating run dock — the one element with a real drop-shadow. Quick / Serious
 * run cards (serious locked until quick succeeds) + conditional rollback. All
 * handlers are passed in; this component owns no state or fetching.
 */
export function RunControlDock({
  manifest,
  seriousUnlocked,
  rollbackTarget,
  starting,
  runsEnabled = true,
  startQuick,
  startSerious,
  rollbackLatestRun,
}: {
  manifest: ShowcaseManifest | null;
  seriousUnlocked: boolean;
  rollbackTarget: ShowcaseRollbackTarget | null;
  starting?: boolean;
  runsEnabled?: boolean;
  startQuick: () => void;
  startSerious: () => void;
  rollbackLatestRun: () => void;
}) {
  const quickSub = manifest
    ? `${manifest.quick_train.length} TRAINING · ${manifest.quick_holdout.length} HOLDOUT`
    : "PREVIEW RUN SET";
  const seriousSub = manifest
    ? `${manifest.serious_train_count} TRAINING · ${manifest.serious_holdout.length} HOLDOUT`
    : "PRODUCTION RUN SET";

  return (
    <GlassPanel
      variant="glass"
      className="flex flex-col gap-4 p-5"
      style={{ boxShadow: "var(--sc-dock-shadow)" }}
    >
      <div className="flex flex-col gap-1">
        <MonoLabel>{DOCK_EYEBROW}</MonoLabel>
        <h2 className="sc-h2" style={{ fontSize: "1.4rem" }}>
          {DOCK_HEADLINE}
        </h2>
      </div>

      {!runsEnabled && (
        <p className="sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text-2)" }} role="status">
          {DOCK_RUNS_DISABLED}
        </p>
      )}

      <div className="flex flex-col gap-3">
        <div className="sc-panel-sunken flex flex-col gap-3 p-4">
          <div className="flex flex-col gap-1">
            <span className="sc-serif" style={{ color: "var(--sc-text)", fontSize: "1.05rem" }}>
              {DOCK_QUICK_TITLE}
            </span>
            <MonoLabel style={{ letterSpacing: "0.08em" }}>{quickSub}</MonoLabel>
          </div>
          <BlockedActionTooltip show={!runsEnabled}>
            <IgniteButton
              variant="primary"
              onClick={startQuick}
              disabled={!runsEnabled || starting}
              className="w-full"
            >
              {starting ? "Starting…" : DOCK_QUICK_CTA}
            </IgniteButton>
          </BlockedActionTooltip>
        </div>

        <div className="sc-panel-sunken flex flex-col gap-3 p-4">
          <div className="flex flex-col gap-1">
            <span className="sc-serif" style={{ color: "var(--sc-text)", fontSize: "1.05rem" }}>
              {DOCK_SERIOUS_TITLE}
            </span>
            <MonoLabel style={{ letterSpacing: "0.08em" }}>
              {seriousUnlocked ? seriousSub : DOCK_SERIOUS_LOCKED}
            </MonoLabel>
          </div>
          <BlockedActionTooltip show={!runsEnabled}>
            <IgniteButton
              variant="secondary"
              onClick={startSerious}
              disabled={!runsEnabled || !seriousUnlocked}
              className="w-full"
            >
              {DOCK_SERIOUS_CTA}
            </IgniteButton>
          </BlockedActionTooltip>
          {rollbackTarget && (
            <BlockedActionTooltip show={!runsEnabled}>
              <IgniteButton
                variant="ghost"
                onClick={rollbackLatestRun}
                disabled={!runsEnabled}
                className="w-full"
              >
                {DOCK_ROLLBACK}
              </IgniteButton>
            </BlockedActionTooltip>
          )}
        </div>
      </div>
    </GlassPanel>
  );
}
