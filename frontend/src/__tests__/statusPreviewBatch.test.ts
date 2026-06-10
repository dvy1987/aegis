import { describe, expect, it } from "vitest";
import { resolveStatusPreviewBatch } from "@/components/showcase/console/statusPreviewBatch";
import type { CaseSummary, ShowcaseManifest, ShowcaseRunSession } from "@/lib/types";

function caseStub(case_id: string): CaseSummary {
  return {
    case_id,
    insurer: "Cigna",
    denial_type: "medical_necessity",
    headline: "h",
    denial_letter_text: "d",
    patient_age: 42,
    patient_gender: "F",
  };
}

const manifest: ShowcaseManifest = {
  benchmark_id: "test",
  version: "1",
  quick_slice: "Cigna:medical_necessity",
  quick_train: Array.from({ length: 5 }, (_, i) => caseStub(`q_train_${i}`)),
  quick_holdout: [caseStub("q_h0"), caseStub("q_h1")],
  serious_train_count: 50,
  serious_holdout: Array.from({ length: 20 }, (_, i) => caseStub(`s_h_${i}`)),
};

function session(partial: Partial<ShowcaseRunSession> = {}): ShowcaseRunSession {
  const base: ShowcaseRunSession = {
    session_id: "sess",
    run_type: "quick",
    status: "running",
    created_at: "",
    updated_at: "",
    case_ids: [],
    diagnostics: {
      stage: "queued",
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
  };
  return {
    ...base,
    ...partial,
    diagnostics: {
      ...base.diagnostics,
      ...partial.diagnostics,
    },
  };
}

describe("resolveStatusPreviewBatch", () => {
  it("shows holdout count before any preview run", () => {
    expect(resolveStatusPreviewBatch(manifest, null, false)).toEqual({ count: 2, verdicts: [] });
  });

  it("falls back to preview holdout when manifest is not loaded yet", () => {
    expect(resolveStatusPreviewBatch(null, null, false)).toEqual({ count: 2, verdicts: [] });
  });

  it("shows serious holdout after preview succeeds", () => {
    const done = session({ run_type: "quick", status: "successful" });
    expect(resolveStatusPreviewBatch(manifest, done, true)).toEqual({ count: 20, verdicts: [] });
  });

  it("shows training count during GEPA", () => {
    const gepa = session({
      diagnostics: { stage: "train_gepa", completed_cases: 0, total_cases: 5 },
    });
    expect(resolveStatusPreviewBatch(manifest, gepa, false)).toEqual({ count: 5, verdicts: [] });
  });

  it("shows scored training post at approval", () => {
    const waiting = session({
      status: "needs_approval",
      diagnostics: { stage: "waiting_for_approval", completed_cases: 5, total_cases: 5 },
      training_post_measure_results: [
        { case_id: "a", verdict: "APPROVE" },
        { case_id: "b", verdict: "DENY" },
      ],
    });
    expect(resolveStatusPreviewBatch(manifest, waiting, false)).toEqual({
      count: 5,
      verdicts: ["APPROVE", "DENY"],
    });
  });

  it("shows holdout lift after promotion", () => {
    const post = session({
      diagnostics: { stage: "measure_after", completed_cases: 1, total_cases: 2 },
      post_measure_results: [{ case_id: "q_h0", verdict: "APPROVE" }],
    });
    expect(resolveStatusPreviewBatch(manifest, post, false)).toEqual({
      count: 2,
      verdicts: ["APPROVE"],
    });
  });
});
