"use client";

import type { ShowcaseManifest, ShowcaseRollbackTarget } from "@/lib/types";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
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
    ? `${manifest.quick_train.length} TRAIN · ${manifest.quick_holdout.length} HOLDOUT · SLICE ${manifest.quick_slice.replaceAll("_", " ").toUpperCase()}`
    : "TARGETED QUICK SET";
  const seriousSub = manifest
    ? `${manifest.serious_train_count} TRAIN · ${manifest.serious_holdout.length} HOLDOUT`
    : "FULL POOL";

  return (
    <GlassPanel
      variant="glass"
      className="flex flex-col gap-4 p-5"
      style={{ boxShadow: "var(--sc-dock-shadow)" }}
    >
      <div className="flex flex-col gap-1">
        <MonoLabel>Current mode</MonoLabel>
        <h2 className="sc-h2" style={{ fontSize: "1.4rem" }}>
          Human-approved learning
        </h2>
      </div>

      <div className="flex flex-col gap-3">
        <div className="sc-panel-sunken flex flex-col gap-3 p-4">
          <div className="flex flex-col gap-1">
            <span className="sc-serif" style={{ color: "var(--sc-text)", fontSize: "1.05rem" }}>
              Quick learning check
            </span>
            <MonoLabel style={{ letterSpacing: "0.08em" }}>{quickSub}</MonoLabel>
          </div>
          <IgniteButton variant="primary" onClick={startQuick} disabled={starting}>
            {starting ? "Starting…" : "Run quick check"}
          </IgniteButton>
        </div>

        <div className="sc-panel-sunken flex flex-col gap-3 p-4">
          <div className="flex flex-col gap-1">
            <span className="sc-serif" style={{ color: "var(--sc-text)", fontSize: "1.05rem" }}>
              Serious learning pass
            </span>
            <MonoLabel style={{ letterSpacing: "0.08em" }}>
              {seriousUnlocked ? seriousSub : "LOCKED UNTIL QUICK SUCCEEDS"}
            </MonoLabel>
          </div>
          <IgniteButton variant="secondary" onClick={startSerious} disabled={!seriousUnlocked}>
            Run serious pass
          </IgniteButton>
          {rollbackTarget && (
            <IgniteButton variant="ghost" onClick={rollbackLatestRun}>
              Roll back latest update
            </IgniteButton>
          )}
        </div>
      </div>
    </GlassPanel>
  );
}
