import { describe, it, expect } from "vitest";
import { flowReducer, initialFlow } from "@/lib/flow/reducer";
import type { AppealFixture } from "@/lib/types";

const fix = {
  run_id: "r",
  appeal_letter: "Dear Cigna",
  outcome: { verdict: "DENY", score: 0.66, threshold: 0.7, feature_scores: [], gaps: [], critique: "", rationale: [] },
  risk_flags: [],
  trace_metadata: {} as never,
  mirror: {} as never,
  citations_used: [],
  missing_evidence_checklist: [],
} as unknown as AppealFixture;

describe("flowReducer", () => {
  it("starts at intake", () => {
    expect(initialFlow.step).toBe("intake");
  });
  it("submit goes to working and keeps the request", () => {
    const s = flowReducer(initialFlow, {
      type: "SUBMIT",
      req: {
        denial_text: "x",
        case_id: "c",
        insurer: "Cigna",
        patient_age: 40,
        patient_gender: "F",
      },
    });
    expect(s.step).toBe("working");
    expect(s.req?.denial_text).toBe("x");
  });
  it("result goes to mirror and holds the fixture", () => {
    const s = flowReducer({ ...initialFlow, step: "working" }, { type: "RESULT", result: fix });
    expect(s.step).toBe("mirror");
    expect(s.result?.appeal_letter).toBe("Dear Cigna");
  });
  it("advances mirror to draft to decide and edits the letter", () => {
    let s = flowReducer({ ...initialFlow, step: "mirror", result: fix }, { type: "ADVANCE" });
    expect(s.step).toBe("draft");
    s = flowReducer(s, { type: "EDIT_LETTER", letter: "edited" });
    expect(s.result?.appeal_letter).toBe("edited");
    s = flowReducer(s, { type: "ADVANCE" });
    expect(s.step).toBe("decide");
  });
  it("error returns to intake with a message", () => {
    const s = flowReducer({ ...initialFlow, step: "working" }, { type: "ERROR", error: "nope" });
    expect(s.step).toBe("intake");
    expect(s.error).toBe("nope");
  });
  it("reset returns to intake", () => {
    expect(flowReducer({ ...initialFlow, step: "decide" }, { type: "RESET" }).step).toBe("intake");
  });
  it("restores a saved flow state", () => {
    const saved = { step: "draft" as const, result: fix, additionalDetails: "note" };
    const s = flowReducer(initialFlow, { type: "RESTORE", state: saved });
    expect(s.step).toBe("draft");
    expect(s.additionalDetails).toBe("note");
  });
  it("stores additional details on the mirror step", () => {
    const s = flowReducer(
      { ...initialFlow, step: "mirror", result: fix },
      { type: "ADD_DETAILS", text: "My oncologist sent labs on June 1." },
    );
    expect(s.additionalDetails).toBe("My oncologist sent labs on June 1.");
    expect(s.step).toBe("mirror");
  });
});
