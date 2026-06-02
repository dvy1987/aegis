import type { DataSource } from "./source";
import type { AppealRequest, AppealFixture, ShowcaseBundle } from "@/lib/types";
import { parseAppealResponse } from "@/lib/schema";
import { getApiBase, getDiscoveryEnabled } from "@/lib/settings";
import { demoSource } from "./demo";

export const liveSource: DataSource = {
  listCases: demoSource.listCases,
  async getShowcase(caseId: string): Promise<ShowcaseBundle> {
    const cases = await demoSource.listCases();
    const found = cases.find((c) => c.case_id === caseId) ?? cases[0];
    const base = getApiBase();
    const res = await fetch(`${base}/v1/showcase/evaluate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        case_id: found.case_id,
        denial_letter_text: found.denial_letter_text,
        clinical_context: found.clinical_context,
        judge_mode: "official",
        run_counterfactual: true,
      }),
    });
    if (!res.ok) throw new Error(`showcase evaluate failed: ${res.status}`);
    return (await res.json()) as ShowcaseBundle;
  },
  async draftAppeal(req: AppealRequest): Promise<AppealFixture> {
    const base = getApiBase();
    const res = await fetch(`${base}/v1/appeal`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...req,
        discovery_enabled: req.discovery_enabled ?? getDiscoveryEnabled(),
      }),
    });
    if (!res.ok) throw new Error(`appeal failed: ${res.status}`);
    const data = parseAppealResponse(await res.json());
    return {
      ...data,
      mirror: {
        insurer: data.trace_metadata.insurer,
        what_was_denied: "See the denial letter you provided.",
        why_they_said_no: "Summarized from your letter.",
        deadline_note: "Check your letter for the appeal deadline and file before that date.",
        strongest_angle: data.outcome.critique || "Review the draft below.",
      },
      citations_used: [],
      missing_evidence_checklist: [],
    };
  },
};
