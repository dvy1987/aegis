import type {
  AppealRequest,
  AppealFixture,
  CaseSummary,
  QuestionStartRequest,
  QuestionTurn,
  ShowcaseBundle,
} from "@/lib/types";

export interface DataSource {
  listCases(): Promise<CaseSummary[]>;
  draftAppeal(req: AppealRequest): Promise<AppealFixture>;
  getShowcase(caseId: string): Promise<ShowcaseBundle>;
  /** Pre-draft interview (appeal flow; traced, not graded). */
  startQuestions(req: QuestionStartRequest): Promise<QuestionTurn>;
  answerQuestion(interviewId: string, answer: string): Promise<QuestionTurn>;
  skipQuestions(interviewId: string): Promise<QuestionTurn>;
}
