import type { ShowcaseManifest } from "@/lib/types";

/** Canonical v1_showcase_100 cohort sizes (preview 5+2, production 50+20). */
export const SHOWCASE_COHORT = {
  quickTrain: 5,
  quickHoldout: 2,
  seriousTrain: 50,
  seriousHoldout: 20,
} as const;

const LEGACY_QUICK_TRAIN = 8;
const LEGACY_SERIOUS_TRAIN = 80;

export type ManifestSource = "api" | "bundled";

function legacyCaseNumber(caseId: string): number | null {
  const match = caseId.match(/^case_(\d+)_/);
  if (!match) return null;
  return Number(match[1]);
}

/** Draft-era cohort used cases 1–100; current showcase preview/production use 101–200. */
export function isLegacyShowcaseManifest(manifest: ShowcaseManifest): boolean {
  if (manifest.quick_train.length === LEGACY_QUICK_TRAIN) return true;
  if (manifest.serious_train_count === LEGACY_SERIOUS_TRAIN) return true;
  for (const row of [...manifest.quick_train, ...manifest.quick_holdout]) {
    const n = legacyCaseNumber(row.case_id);
    if (n != null && n < 101) return true;
  }
  return false;
}

export function cohortMatchesCanonical(manifest: ShowcaseManifest): boolean {
  return (
    manifest.quick_train.length === SHOWCASE_COHORT.quickTrain &&
    manifest.quick_holdout.length === SHOWCASE_COHORT.quickHoldout &&
    manifest.serious_train_count === SHOWCASE_COHORT.seriousTrain &&
    manifest.serious_holdout.length === SHOWCASE_COHORT.seriousHoldout
  );
}

export async function loadBundledShowcaseManifest(): Promise<ShowcaseManifest> {
  const res = await fetch("/showcase-manifest.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`bundled showcase manifest failed: ${res.status}`);
  return (await res.json()) as ShowcaseManifest;
}
