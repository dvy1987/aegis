import { describe, expect, it } from "vitest";
import { CASES } from "@/lib/fixtures/cases";
import { buildAppealMirror, collectPatientGapItems } from "@/lib/flow/buildAppealMirror";
import type { AppealRequest, AppealResponse } from "@/lib/types";

const case168 = CASES[0];

function baseResponse(): AppealResponse {
  return {
    run_id: "test",
    appeal_letter: "draft",
    outcome: {
      verdict: "DENY",
      score: 0,
      threshold: 0.8,
      feature_scores: [],
      gaps: ["hard gate not met: addresses_denial_rationale"],
      critique: "Utilization Management reviewer upholds denial.",
      rationale: [],
    },
    risk_flags: [],
    trace_metadata: {
      case_id: case168.case_id,
      insurer: case168.insurer,
      denial_type: "prior_authorization",
      plan_type: "commercial",
      state: "unknown",
      prompt_version: "drafter_v1_1",
      playbook_version: "us",
      dataset_split: "holdout",
      run_mode: "interactive",
    },
    question_interview: {
      qa_transcript: [
        {
          turn: 1,
          question: "Have you tried other medications?",
          answer: "This is my first treatment for leukemia.",
        },
      ],
      planned_questions: ["Did your oncologist send a letter to Aetna?"],
      patient_gap_note:
        "We drafted your appeal with the information available. Answers to these questions could make it stronger:\n- Did your oncologist send a letter to Aetna?",
      skipped: false,
    },
  };
}

describe("buildAppealMirror", () => {
  it("never uses simulator critique", () => {
    const req: AppealRequest = {
      denial_text: case168.denial_letter_text,
      case_id: case168.case_id,
      insurer: case168.insurer,
      patient_age: case168.patient_age,
      patient_gender: case168.patient_gender,
      clinical_context: case168.clinical_context,
    };
    const mirror = buildAppealMirror(req, baseResponse());
    expect(mirror.gaps_note).not.toMatch(/Utilization Management|reviewer|hard gate/i);
    expect(mirror.what_was_denied).toMatch(/venetoclax/i);
    expect(mirror.what_was_denied).not.toMatch(/see the denial|you provided/i);
    expect(mirror.why_they_said_no).toMatch(/non-preferred|preferred alternative/i);
    expect(mirror.why_they_said_no).not.toMatch(/summarized from/i);
    expect(mirror.what_helps_note).toMatch(/first treatment/i);
    expect(mirror.what_helps_note).not.toMatch(/I'm not sure/i);
    expect(mirror.gaps_note).toMatch(/oncologist.*letter/i);
    expect(mirror.gaps_note).toMatch(/preferred alternative/i);
    expect(mirror.gaps_note).toMatch(/oncologist send a letter/i);
  });

  it("collects patient gaps without simulator strings", () => {
    const req: AppealRequest = {
      denial_text: case168.denial_letter_text,
      case_id: case168.case_id,
      insurer: case168.insurer,
      patient_age: case168.patient_age,
      patient_gender: case168.patient_gender,
    };
    const items = collectPatientGapItems(req, baseResponse().question_interview);
    expect(items.some((i) => /preferred alternative/i.test(i))).toBe(true);
    expect(items.some((i) => /hard gate/i.test(i))).toBe(false);
  });
});
