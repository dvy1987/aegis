import type { ShowcaseManifest } from "@/lib/types";

export type InactiveStatusNarrative = {
  /** Omitted before the first preview run — nothing to report yet. */
  justNow: string | null;
  upNext: string;
};

const FALLBACK = { quickHoldout: 2, seriousHoldout: 20 } as const;

/** Sparse copy for the idle session status panel (no active run). */
export function resolveInactiveStatusNarrative(
  manifest: ShowcaseManifest | null,
  seriousUnlocked: boolean,
): InactiveStatusNarrative {
  if (seriousUnlocked) {
    const holdout = manifest?.serious_holdout.length ?? FALLBACK.seriousHoldout;
    return {
      justNow: "Preview run completed.",
      upNext: `Production holdout baseline · ${holdout} cases · drafter as-shipped · learning off`,
    };
  }

  const holdout = manifest?.quick_holdout.length ?? FALLBACK.quickHoldout;
  const caseLabel = holdout === 1 ? "case" : "cases";
  return {
    justNow: null,
    upNext: `Preview holdout · ${holdout} ${caseLabel} · baseline drafter agent · learning off`,
  };
}
