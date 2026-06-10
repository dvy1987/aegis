import type { ShowcaseManifest, ShowcaseRunSession } from "@/lib/types";

export type StatusPreviewBatch = {
  count: number;
  verdicts: string[];
};

/** Manifest API fallback — matches v1_showcase_100 quick/serious split. */
const FALLBACK_COHORT = {
  quickHoldout: 2,
  quickTrain: 5,
  seriousHoldout: 20,
  seriousTrain: 50,
} as const;

function cohortSizes(manifest: ShowcaseManifest, runType: "quick" | "serious") {
  if (runType === "quick") {
    return {
      holdout: manifest.quick_holdout.length,
      train: manifest.quick_train.length,
    };
  }
  return {
    holdout: manifest.serious_holdout.length,
    train: manifest.serious_train_count,
  };
}

function verdictsFrom(results: Record<string, unknown>[]): string[] {
  return results.map((row) => String(row.verdict ?? "").toUpperCase()).filter(Boolean);
}

/**
 * How many case tiles the session status panel should preview, and which are
 * already scored. Counts follow the showcase runner order: holdout baseline →
 * training pre → GEPA → training post → approval → holdout lift.
 */
export function resolveStatusPreviewBatch(
  manifest: ShowcaseManifest | null,
  session: ShowcaseRunSession | null,
  seriousUnlocked: boolean,
): StatusPreviewBatch {
  if (!session) {
    if (manifest) {
      const count = seriousUnlocked ? manifest.serious_holdout.length : manifest.quick_holdout.length;
      return { count, verdicts: [] };
    }
    const count = seriousUnlocked ? FALLBACK_COHORT.seriousHoldout : FALLBACK_COHORT.quickHoldout;
    return { count, verdicts: [] };
  }

  if (!manifest) return { count: 0, verdicts: [] };

  const { holdout, train } = cohortSizes(manifest, session.run_type);
  const { stage, total_cases: totalCases } = session.diagnostics;
  const { status } = session;

  if (status === "successful") {
    if (session.run_type === "quick") {
      return { count: manifest.serious_holdout.length, verdicts: [] };
    }
    return { count: holdout, verdicts: verdictsFrom(session.post_measure_results) };
  }

  if (status === "needs_approval" || stage === "waiting_for_approval") {
    return { count: train, verdicts: verdictsFrom(session.training_post_measure_results) };
  }

  if (stage === "train_gepa") {
    return { count: train, verdicts: [] };
  }

  if (stage === "measure_after") {
    if (totalCases === train) {
      return { count: train, verdicts: verdictsFrom(session.training_post_measure_results) };
    }
    return { count: holdout, verdicts: verdictsFrom(session.post_measure_results) };
  }

  if (stage === "promote") {
    return { count: holdout, verdicts: verdictsFrom(session.post_measure_results) };
  }

  if (stage === "measure_before") {
    if (totalCases === holdout) {
      return { count: holdout, verdicts: verdictsFrom(session.pre_measure_results) };
    }
    if (totalCases === train) {
      return { count: train, verdicts: verdictsFrom(session.training_pre_measure_results) };
    }
    if (session.pre_measure_results.length < holdout) {
      return { count: holdout, verdicts: verdictsFrom(session.pre_measure_results) };
    }
    return { count: train, verdicts: verdictsFrom(session.training_pre_measure_results) };
  }

  if (stage === "queued") {
    return { count: holdout, verdicts: [] };
  }

  if (totalCases > 0) {
    return { count: totalCases, verdicts: [] };
  }

  return { count: holdout, verdicts: [] };
}
