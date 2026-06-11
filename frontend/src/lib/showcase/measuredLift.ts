import type {
  MeasuredLiftCache,
  MeasuredLiftCasePersisted,
  ShowcaseMeasureVariant,
} from "@/lib/types";

export function measuredLiftFromPersisted(
  persisted: Record<string, MeasuredLiftCasePersisted>,
): MeasuredLiftCache {
  const out: MeasuredLiftCache = {};
  for (const [caseId, entry] of Object.entries(persisted)) {
    const row: NonNullable<MeasuredLiftCache[string]> = {};
    if (entry.baseline) row.baseline = entry.baseline;
    if (entry.candidate) row.candidate = entry.candidate;
    if (row.baseline || row.candidate) out[caseId] = row as NonNullable<MeasuredLiftCache[string]>;
  }
  return out;
}
