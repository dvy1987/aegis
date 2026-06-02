import type { DataSource } from "./source";
import type { AppealRequest, AppealFixture } from "@/lib/types";
import { parseAppealResponse } from "@/lib/schema";
import { getApiBase, getDiscoveryEnabled } from "@/lib/settings";
import { demoSource } from "./demo";

export const liveSource: DataSource = {
  listCases: demoSource.listCases,
  getShowcase: demoSource.getShowcase,
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
