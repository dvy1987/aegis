import type { DataSource } from "./source";
import type { AppealRequest, AppealFixture } from "@/lib/types";
import { parseAppealResponse } from "@/lib/schema";
import { demoSource } from "./demo";

const BASE = process.env.NEXT_PUBLIC_AEGIS_API ?? "http://localhost:8001";

// Live mode calls the FastAPI backend for drafting. listCases / getShowcase reuse the
// bundled artifacts — the showcase is always recorded evidence, never live-generated.
export const liveSource: DataSource = {
  listCases: demoSource.listCases,
  getShowcase: demoSource.getShowcase,
  async draftAppeal(req: AppealRequest): Promise<AppealFixture> {
    const res = await fetch(`${BASE}/v1/appeal`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`appeal failed: ${res.status}`);
    const data = parseAppealResponse(await res.json());
    // The live API does not return parsed_case / appeal_strategy (spec section 6.1),
    // so synthesize a lighter Mirror from what the response does carry.
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
