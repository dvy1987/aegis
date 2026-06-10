import type { ShowcaseManifest, ShowcaseRunSession } from "@/lib/types";

export type MatrixTab = "quick" | "serious";

export type MatrixSlot = {
  caseId: string;
  verdict: string;
};

export type MatrixCohort = {
  holdoutIds: string[];
  trainIds: string[];
};

/** Expected case ids per cohort — from manifest, refined by live session when available. */
export function resolveMatrixCohort(
  manifest: ShowcaseManifest,
  tab: MatrixTab,
  session: ShowcaseRunSession | null,
): MatrixCohort {
  if (tab === "quick") {
    return {
      holdoutIds: manifest.quick_holdout.map((c) => c.case_id),
      trainIds: manifest.quick_train.map((c) => c.case_id),
    };
  }

  const holdoutIds = manifest.serious_holdout.map((c) => c.case_id);
  let trainIds = Array.from(
    { length: manifest.serious_train_count },
    (_, i) => `__serious_train_${i}`,
  );

  if (session?.run_type === "serious" && session.case_ids.length > 0) {
    const holdoutSet = new Set(holdoutIds);
    const fromSession = session.case_ids.filter((id) => !holdoutSet.has(id));
    if (fromSession.length > 0) trainIds = fromSession;
  }

  return { holdoutIds, trainIds };
}

/** Map measurement results onto fixed slots; missing cases stay pending (grey). */
export function mergeResultSlots(caseIds: string[], results: Record<string, unknown>[]): MatrixSlot[] {
  const byId = new Map<string, string>();
  for (const row of results) {
    const id = String(row.case_id ?? "");
    if (!id) continue;
    byId.set(id, String(row.verdict ?? ""));
  }

  return caseIds.map((caseId, index) => ({
    caseId: caseId.startsWith("__") ? `train ${index + 1}` : caseId,
    verdict: byId.get(caseId) ?? "",
  }));
}

/** Production training only: 50 cases → 25 + 25. Everything else uses the default small grid. */
export function productionRowColumns(count: number, tab: MatrixTab): number | null {
  if (tab !== "serious" || count !== 50) return null;
  return 25;
}
