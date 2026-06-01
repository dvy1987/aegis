import type { AppealRequest, AppealFixture, CaseSummary, ShowcaseBundle } from "@/lib/types";

export interface DataSource {
  listCases(): Promise<CaseSummary[]>;
  draftAppeal(req: AppealRequest): Promise<AppealFixture>;
  getShowcase(caseId: string): Promise<ShowcaseBundle>;
}
