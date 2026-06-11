import type { DataSource } from "./source";
import type {
  AppealRequest,
  AppealFixture,
  CaseSummary,
  QuestionStartRequest,
  QuestionTurn,
  ShowcaseBundle,
  ShowcaseManifest,
  ShowcaseMeasureResult,
  ShowcaseMeasureVariant,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import {
  cohortMatchesCanonical,
  isLegacyShowcaseManifest,
  loadBundledShowcaseManifest,
} from "@/lib/showcase/manifest";
import { parseAppealResponse, parseQuestionTurn, simulatorResultSchema } from "@/lib/schema";
import { formatFetchError } from "@/lib/apiErrors";
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
  async startQuestions(req: QuestionStartRequest): Promise<QuestionTurn> {
    const base = getApiBase();
    const res = await fetch(`${base}/v1/appeal/questions/start`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`questions start failed: ${res.status}`);
    return parseQuestionTurn(await res.json());
  },
  async answerQuestion(interviewId: string, answer: string): Promise<QuestionTurn> {
    const base = getApiBase();
    const res = await fetch(`${base}/v1/appeal/questions/${interviewId}/answer`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ answer }),
    });
    if (!res.ok) throw new Error(`questions answer failed: ${res.status}`);
    return parseQuestionTurn(await res.json());
  },
  async skipQuestions(interviewId: string): Promise<QuestionTurn> {
    const base = getApiBase();
    const res = await fetch(`${base}/v1/appeal/questions/${interviewId}/skip`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`questions skip failed: ${res.status}`);
    return parseQuestionTurn(await res.json());
  },
  async runShowcaseMeasure(
    caseSummary: CaseSummary,
    variant: ShowcaseMeasureVariant,
  ): Promise<ShowcaseMeasureResult> {
    const base = getApiBase();

    let res: Response;
    try {
      res = await fetch(`${base}/v1/showcase/measure-case`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          case_id: caseSummary.case_id,
          denial_letter_text: caseSummary.denial_letter_text,
          clinical_context: caseSummary.clinical_context ?? "",
          insurer: caseSummary.insurer,
          denial_type: caseSummary.denial_type,
          patient_age: caseSummary.patient_age,
          patient_gender: caseSummary.patient_gender,
          variant,
        }),
      });
    } catch (error) {
      throw new Error(formatFetchError(error, base, "Measured-lift simulator"));
    }

    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(
        `Measured-lift simulator failed (${res.status})${detail ? ` — ${detail.slice(0, 240)}` : ""}`,
      );
    }
    const data = (await res.json()) as ShowcaseMeasureResult;
    return {
      ...data,
      outcome: simulatorResultSchema.parse(data.outcome),
    };
  },
};

async function jsonOrThrow<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) throw new Error(`${label} failed: ${res.status}`);
  return (await res.json()) as T;
}

export type ShowcaseManifestLoad = {
  manifest: ShowcaseManifest;
  /** Shown when the API still serves the retired 8/80 draft cohort. */
  legacyApiWarning: string | null;
};

export async function resolveShowcaseManifest(): Promise<ShowcaseManifestLoad> {
  const base = getApiBase();
  const legacyWarning =
    "Showcase API is on the legacy 8/80 cohort. The grid uses the bundled 3/1 + 5/2 manifest. Redeploy aegis-v1-api (or point NEXT_PUBLIC_AEGIS_API at a current backend) before starting a run.";

  try {
    const res = await fetch(`${base}/v1/showcase/manifest`, { cache: "no-store" });
    if (!res.ok) throw new Error(`showcase manifest failed: ${res.status}`);
    const api = (await res.json()) as ShowcaseManifest;
    if (cohortMatchesCanonical(api) && !isLegacyShowcaseManifest(api)) {
      return { manifest: api, legacyApiWarning: null };
    }
    return {
      manifest: await loadBundledShowcaseManifest(),
      legacyApiWarning: legacyWarning,
    };
  } catch {
    return {
      manifest: await loadBundledShowcaseManifest(),
      legacyApiWarning: null,
    };
  }
}

export async function getShowcaseManifest(): Promise<ShowcaseManifest> {
  return (await resolveShowcaseManifest()).manifest;
}

export async function startQuickRun(): Promise<ShowcaseRunSession> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRunSession>(
    await fetch(`${base}/v1/showcase/runs/quick`, { method: "POST" }),
    "quick run",
  );
}

export async function startSeriousRun(): Promise<ShowcaseRunSession> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRunSession>(
    await fetch(`${base}/v1/showcase/runs/serious`, { method: "POST" }),
    "serious run",
  );
}

export async function getRunSession(sessionId: string): Promise<ShowcaseRunSession> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRunSession>(
    await fetch(`${base}/v1/showcase/runs/${sessionId}`),
    "run status",
  );
}

export async function cancelRun(sessionId: string): Promise<ShowcaseRunSession> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRunSession>(
    await fetch(`${base}/v1/showcase/runs/${sessionId}/cancel`, { method: "POST" }),
    "cancel run",
  );
}

export async function resumeRun(sessionId: string): Promise<ShowcaseRunSession> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRunSession>(
    await fetch(`${base}/v1/showcase/runs/${sessionId}/resume`, { method: "POST" }),
    "resume run",
  );
}

export async function approveRun(sessionId: string): Promise<ShowcaseRunSession> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRunSession>(
    await fetch(`${base}/v1/showcase/runs/${sessionId}/approve`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ approver: "pm" }),
    }),
    "approve run",
  );
}

export async function rejectRun(sessionId: string): Promise<ShowcaseRunSession> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRunSession>(
    await fetch(`${base}/v1/showcase/runs/${sessionId}/reject`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ reviewer: "pm" }),
    }),
    "reject run",
  );
}

export async function getRollbackTarget(): Promise<ShowcaseRollbackTarget | null> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRollbackTarget | null>(
    await fetch(`${base}/v1/showcase/rollback-target`),
    "rollback target",
  );
}

export async function rollbackRun(): Promise<ShowcaseRollbackTarget> {
  const base = getApiBase();
  return jsonOrThrow<ShowcaseRollbackTarget>(
    await fetch(`${base}/v1/showcase/rollback`, { method: "POST" }),
    "rollback run",
  );
}
