import type { DataSource } from "./source";
import type { AppealRequest, AppealFixture, ShowcaseBundle } from "@/lib/types";
import { CASES } from "@/lib/fixtures/cases";
import { parseAppealFixture } from "@/lib/schema";

const FALLBACK = "case_13_cigna_mednec";

export const demoSource: DataSource = {
  async listCases() {
    return CASES;
  },
  async draftAppeal(req: AppealRequest): Promise<AppealFixture> {
    const id = CASES.some((c) => c.case_id === req.case_id) ? req.case_id : FALLBACK;
    const mod = await import(`@/lib/fixtures/appeals/${id}.json`);
    return parseAppealFixture(mod.default);
  },
  async getShowcase(caseId: string): Promise<ShowcaseBundle> {
    const id = CASES.some((c) => c.case_id === caseId) ? caseId : FALLBACK;
    const mod = await import(`@/lib/fixtures/showcase/${id}.json`);
    return mod.default as ShowcaseBundle;
  },
};
