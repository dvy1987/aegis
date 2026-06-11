import { describe, expect, it } from "vitest";
import { isAfterLearningUnlocked } from "@/lib/showcase/simulatorUnlock";
import type { ShowcaseRollbackTarget, ShowcaseRunSession } from "@/lib/types";

function session(partial: Partial<ShowcaseRunSession>): ShowcaseRunSession {
  return {
    session_id: "s",
    run_type: "quick",
    status: "running",
    created_at: "",
    updated_at: "",
    case_ids: [],
    diagnostics: {
      stage: "promote",
      completed_cases: 0,
      total_cases: 0,
      retryable: false,
      phoenix_trace_ids: [],
      cloud_log_filter: "",
    },
    cancelled: false,
    pre_measure_results: [],
    training_pre_measure_results: [],
    training_post_measure_results: [],
    post_measure_results: [],
    regression_detected: false,
    ...partial,
  };
}

const rollback: ShowcaseRollbackTarget = {
  run_type: "quick",
  session_id: "s",
  promoted_at: "2026-01-01T00:00:00Z",
  candidate_id: "c1",
  files: [],
};

describe("isAfterLearningUnlocked", () => {
  it("is locked with no session and no promotion checkpoint", () => {
    expect(isAfterLearningUnlocked(null, null)).toBe(false);
  });

  it("unlocks while waiting for approval", () => {
    expect(
      isAfterLearningUnlocked(
        session({ status: "needs_approval", approved_by: null }),
        null,
      ),
    ).toBe(false);
  });

  it("unlocks after approval is recorded", () => {
    expect(
      isAfterLearningUnlocked(
        session({ status: "running", approved_by: "pm" }),
        null,
      ),
    ).toBe(true);
  });

  it("unlocks from promotion checkpoint alone", () => {
    expect(isAfterLearningUnlocked(null, rollback)).toBe(true);
  });

  it("locks again after rollback", () => {
    expect(
      isAfterLearningUnlocked(
        session({ status: "rolled_back", approved_by: "pm" }),
        null,
      ),
    ).toBe(false);
  });
});
