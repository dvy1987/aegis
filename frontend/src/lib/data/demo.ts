import type { DataSource } from "./source";
import type {
  AppealRequest,
  AppealFixture,
  QuestionTurn,
  ShowcaseBundle,
  ShowcaseMeasureResult,
  ShowcaseMeasureVariant,
} from "@/lib/types";
import { CASES } from "@/lib/fixtures/cases";
import { parseAppealFixture } from "@/lib/schema";

const FALLBACK = "case_12_aetna_priorauth";

const SHOWCASE_CASE_IDS = new Set(CASES.map((c) => c.case_id));

async function loadAppealFixture(caseId: string): Promise<AppealFixture> {
  const id = CASES.some((c) => c.case_id === caseId) ? caseId : FALLBACK;
  const mod = await import(`@/lib/fixtures/appeals/${id}.json`);
  return parseAppealFixture(mod.default);
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
    if (SHOWCASE_CASE_IDS.has(req.case_id)) {
      throw new Error(
        "Measured-lift showcase cases draft live via the backend only — connect the API in Settings.",
      );
    }
    return loadAppealFixture(req.case_id);
  },
  async runShowcaseMeasure(): Promise<ShowcaseMeasureResult> {
    throw new Error(
      "Showcase simulator requires the live backend (v2 simulator + day-zero baseline). Connect the API in Settings.",
    );
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
