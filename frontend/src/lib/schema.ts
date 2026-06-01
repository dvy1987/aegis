import { z } from "zod";

const anchor = z.union([z.literal(1), z.literal(3), z.literal(5)]);
const verdict = z.enum(["APPROVE", "DENY"]);

export const featureScoreSchema = z.object({
  feature: z.string(), anchor, weight: z.number(),
  must_have: z.boolean(), evidence: z.string().default(""),
});

export const simulatorResultSchema = z.object({
  verdict, score: z.number(), threshold: z.number(),
  feature_scores: z.array(featureScoreSchema).default([]),
  gaps: z.array(z.string()).default([]),
  critique: z.string().default(""), rationale: z.array(z.string()).default([]),
});

export const traceMetadataSchema = z.object({
  case_id: z.string(), insurer: z.string(), denial_type: z.string(),
  plan_type: z.string(), state: z.string(), prompt_version: z.string(),
  playbook_version: z.string(), dataset_split: z.string(),
  run_mode: z.enum(["interactive", "benchmark", "autonomous_promotion"]),
});

export const appealResponseSchema = z.object({
  run_id: z.string(), appeal_letter: z.string(),
  outcome: simulatorResultSchema, risk_flags: z.array(z.string()).default([]),
  trace_metadata: traceMetadataSchema,
});

export const mirrorBlockSchema = z.object({
  insurer: z.string(), what_was_denied: z.string(), why_they_said_no: z.string(),
  deadline_note: z.string(), strongest_angle: z.string(),
});

export const appealFixtureSchema = appealResponseSchema.extend({
  mirror: mirrorBlockSchema,
  citations_used: z.array(z.object({ title: z.string(), quote: z.string() })).default([]),
  missing_evidence_checklist: z.array(z.string()).default([]),
});

// Reject any teacher answer-key field leaking into a consumer fixture (firewall INV-2).
export const FORBIDDEN_FIXTURE_KEYS = [
  "synthetic_provenance", "appeal_difficulty", "exploitable_weaknesses",
  "strong_defenses", "critic_verdicts", "intended_flaw_types",
];

export function parseAppealResponse(x: unknown) { return appealResponseSchema.parse(x); }
export function parseAppealFixture(x: unknown) { return appealFixtureSchema.parse(x); }
