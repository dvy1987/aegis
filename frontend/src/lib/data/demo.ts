import type { DataSource } from "./source";
import type {
  AppealRequest,
  AppealFixture,
  CaseSummary,
  QuestionTurn,
  ShowcaseBundle,
  ShowcaseMeasureResult,
  ShowcaseMeasureVariant,
} from "@/lib/types";
import { CASES } from "@/lib/fixtures/cases";
import { parseAppealFixture } from "@/lib/schema";

const FALLBACK = "case_168_aetna_priorauth";

function excerpt(text: string, limit = 520): string {
  const compact = text.replace(/\s+/g, " ").trim();
  return compact.length > limit ? `${compact.slice(0, limit)}...` : compact;
}

async function loadAppealFixture(caseId: string): Promise<AppealFixture> {
  const id = CASES.some((c) => c.case_id === caseId) ? caseId : FALLBACK;
  const mod = await import(`@/lib/fixtures/appeals/${id}.json`);
  return parseAppealFixture(mod.default);
}

function demoMeasureResult(
  fixture: AppealFixture,
  variant: ShowcaseMeasureVariant,
): ShowcaseMeasureResult {
  const baselineOutcome = {
    ...fixture.outcome,
    score: Math.max(0, fixture.outcome.score - 0.08),
    verdict: "DENY" as const,
  };
  const boosted =
    variant === "candidate"
      ? {
          ...fixture.outcome,
          score: Math.min(1, fixture.outcome.score + 0.09),
          verdict:
            fixture.outcome.score + 0.09 >= fixture.outcome.threshold
              ? ("APPROVE" as const)
              : fixture.outcome.verdict,
        }
      : baselineOutcome;

  return {
    case_id: fixture.trace_metadata.case_id,
    variant,
    verdict: boosted.verdict,
    score: boosted.score,
    threshold: boosted.threshold,
    letter_excerpt: excerpt(fixture.appeal_letter),
    appeal_letter: fixture.appeal_letter,
    outcome: boosted,
    prompt_version: variant === "baseline" ? "drafter_v1 · day_zero" : "promoted · phoenix on",
    risk_flags:
      variant === "baseline"
        ? [...fixture.risk_flags, "phoenix_mcp_request_disabled", "playbook:day_zero"]
        : [...fixture.risk_flags, "phoenix_mcp_live"],
  };
}

// Canned offline interview: two questions, then done. Keeps the questions
// step demoable without the backend.
const DEMO_QUESTIONS = [
  "When did your symptoms start, and how do they affect your daily life?",
  "Have you tried other treatments for this before, and what happened?",
];
const demoInterviews = new Map<string, number>();

function demoTurn(id: string, asked: number): QuestionTurn {
  const done = asked >= DEMO_QUESTIONS.length;
  return {
    interview_id: id,
    question: done ? null : DEMO_QUESTIONS[asked],
    turn: Math.min(asked + 1, DEMO_QUESTIONS.length),
    done,
    planned_questions: done ? DEMO_QUESTIONS : [],
    patient_gap_note: "",
  };
}

export const demoSource: DataSource = {
  async listCases() {
    return CASES;
  },
  async draftAppeal(req: AppealRequest): Promise<AppealFixture> {
    return loadAppealFixture(req.case_id);
  },
  async runShowcaseMeasure(
    caseSummary: CaseSummary,
    variant: ShowcaseMeasureVariant,
  ): Promise<ShowcaseMeasureResult> {
    const fixture = await loadAppealFixture(caseSummary.case_id);
    return demoMeasureResult(fixture, variant);
  },
  async startQuestions(): Promise<QuestionTurn> {
    const id = `demo-${Date.now()}`;
    demoInterviews.set(id, 0);
    return demoTurn(id, 0);
  },
  async answerQuestion(interviewId: string): Promise<QuestionTurn> {
    const asked = (demoInterviews.get(interviewId) ?? 0) + 1;
    demoInterviews.set(interviewId, asked);
    return demoTurn(interviewId, asked);
  },
  async skipQuestions(interviewId: string): Promise<QuestionTurn> {
    const asked = demoInterviews.get(interviewId) ?? 0;
    return {
      ...demoTurn(interviewId, DEMO_QUESTIONS.length),
      turn: asked,
      planned_questions: DEMO_QUESTIONS,
      patient_gap_note:
        "We drafted with what you provided. Answers to the listed questions could make it stronger.",
    };
  },
  async getShowcase(caseId: string): Promise<ShowcaseBundle> {
    const id = CASES.some((c) => c.case_id === caseId) ? caseId : FALLBACK;
    const mod = await import(`@/lib/fixtures/showcase/${id}.json`);
    const data = mod.default;
    
    // Fallback if the fixture was overwritten by the sync script
    if (!data.v1) {
      return {
        case_id: id,
        measured: false,
        v1: { composite: 0, verdict: "DENY", letter_excerpt: "" },
        v3: { composite: 0, verdict: "DENY", letter_excerpt: "" },
        lift_relative_pct: 0,
        what_changed: [],
        counterfactual: { on_composite: 0, off_composite: 0 },
      };
    }
    
    return data as ShowcaseBundle;
  },
};
