import { describe, expect, it } from "vitest";
import { measuredLiftFromPersisted } from "@/lib/showcase/measuredLift";

describe("measuredLiftFromPersisted", () => {
  it("maps baseline and candidate columns per case", () => {
    const cache = measuredLiftFromPersisted({
      case_168_aetna_priorauth: {
        baseline: {
          case_id: "case_168_aetna_priorauth",
          variant: "baseline",
          verdict: "DENY",
          score: 0.2,
          threshold: 0.7,
          letter_excerpt: "a",
          appeal_letter: "letter",
          outcome: {
            verdict: "DENY",
            score: 0.2,
            threshold: 0.7,
            feature_scores: [],
            gaps: [],
            critique: "",
            rationale: [],
          },
          prompt_version: "drafter_v1",
          risk_flags: [],
        },
      },
    });
    expect(cache.case_168_aetna_priorauth?.baseline?.score).toBe(0.2);
  });
});
