import { describe, it, expect } from "vitest";
import { parseAppealResponse, parseAppealFixture } from "@/lib/schema";

const valid = {
  run_id: "r1", appeal_letter: "Dear Cigna,", risk_flags: [],
  outcome: { verdict: "DENY", score: 0.66, threshold: 0.7, feature_scores: [], gaps: ["weak: grounding (anchor 3)"], critique: "", rationale: [] },
  trace_metadata: { case_id: "c1", insurer: "Cigna", denial_type: "medical_necessity", plan_type: "commercial", state: "unknown", prompt_version: "aegis_v1_weak", playbook_version: "cold-start", dataset_split: "interactive", run_mode: "interactive" },
};

describe("parseAppealResponse", () => {
  it("accepts a valid response", () => {
    expect(parseAppealResponse(valid).outcome.verdict).toBe("DENY");
  });
  it("rejects an invalid verdict", () => {
    expect(() => parseAppealResponse({ ...valid, outcome: { ...valid.outcome, verdict: "MAYBE" } })).toThrow();
  });
});

describe("parseAppealFixture", () => {
  it("requires the mirror block", () => {
    expect(() => parseAppealFixture(valid)).toThrow();
  });
});
