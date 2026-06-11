import type { ShowcaseRollbackTarget, ShowcaseRunSession } from "@/lib/types";

const BLOCKED_AFTER_STATUSES = new Set([
  "rejected",
  "cancelled",
  "rolled_back",
]);

/**
 * After-learning actions (simulator, draft) unlock once a GEPA proposal from a
 * preview or production run has been approved and promoted — or when a promotion
 * checkpoint still exists on disk (survives page refresh).
 */
export function isAfterLearningUnlocked(
  runSession: ShowcaseRunSession | null,
  rollbackTarget: ShowcaseRollbackTarget | null,
): boolean {
  if (rollbackTarget) return true;
  if (!runSession?.approved_by) return false;
  return !BLOCKED_AFTER_STATUSES.has(runSession.status);
}
