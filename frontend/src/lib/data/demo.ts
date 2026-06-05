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
    const data = mod.default;
    
    // Fallback if the fixture was overwritten by the sync script
    if (!data.v1) {
      return {
        case_id: id,
        measured: false,
        v1: { composite: 0.5, verdict: "DENY", letter_excerpt: "Missing data" },
        v3: { composite: 0.9, verdict: "APPROVE", letter_excerpt: "Missing data" },
        lift_relative_pct: 80,
        what_changed: ["Missing data - click Run Live to generate"],
        counterfactual: { on_composite: 0.9, off_composite: 0.5 },
      };
    }
    
    return data as ShowcaseBundle;
  },
};
