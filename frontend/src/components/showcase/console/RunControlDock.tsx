"use client";

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
  DOCK_SERIOUS_LOCKED,
  DOCK_SERIOUS_TITLE,
} from "@/components/showcase/copy";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";

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
  startQuick,
  startSerious,
  rollbackLatestRun,
}: {
  manifest: ShowcaseManifest | null;
  seriousUnlocked: boolean;
  rollbackTarget: ShowcaseRollbackTarget | null;
  starting?: boolean;
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

      <div className="flex flex-col gap-3">
        <div className="sc-panel-sunken flex flex-col gap-3 p-4">
          <div className="flex flex-col gap-1">
            <span className="sc-serif" style={{ color: "var(--sc-text)", fontSize: "1.05rem" }}>
              {DOCK_QUICK_TITLE}
            </span>
            <MonoLabel style={{ letterSpacing: "0.08em" }}>{quickSub}</MonoLabel>
          </div>
          <IgniteButton variant="primary" onClick={startQuick} disabled={starting}>
            {starting ? "Starting…" : DOCK_QUICK_CTA}
          </IgniteButton>
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
          <IgniteButton variant="secondary" onClick={startSerious} disabled={!seriousUnlocked}>
            {DOCK_SERIOUS_CTA}
          </IgniteButton>
          {rollbackTarget && (
            <IgniteButton variant="ghost" onClick={rollbackLatestRun}>
              {DOCK_ROLLBACK}
            </IgniteButton>
          )}
        </div>
      </div>
    </GlassPanel>
  );
}
