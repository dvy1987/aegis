// Core shapes mirror backend/app/aegis_v1/schemas.py; AppealRequest/AppealResponse
// mirror backend/app/aegis_v1/appeal_api.py (the wire contract). Keep field names in sync.
export type Verdict = "APPROVE" | "DENY";
export type Anchor = 1 | 3 | 5;

export interface FeatureScore {
  feature: string;
  anchor: Anchor;
  weight: number;
  must_have: boolean;
  evidence: string;
}

export interface SimulatorResult {
  verdict: Verdict;
  score: number;       // 0..1
  threshold: number;   // e.g. 0.70
  feature_scores: FeatureScore[];
  gaps: string[];      // empty on APPROVE
  critique: string;
  rationale: string[];
}

export interface TraceMetadata {
  case_id: string;
  insurer: string;
  denial_type: string;
  plan_type: string;
  state: string;
  prompt_version: string;
  playbook_version: string;
  dataset_split: string;
  run_mode: "interactive" | "benchmark" | "autonomous_promotion";
}

export type InsurerPin = "Aetna" | "Cigna" | "UHC";
export type PatientGender = "F" | "M" | "X";

export interface AppealRequest {
  denial_text: string;
  case_id: string;
  insurer: InsurerPin;
  patient_age: number;
  patient_gender: PatientGender;
  /** Optional free-form clinical note from the person or their doctor. */
  clinical_context?: string;
  /** When true (live mode only), backend may fetch up to 5 trusted sources if library is thin. */
  discovery_enabled?: boolean;
  /** Finished pre-draft interview (questions step); enriches the draft context. */
  interview_id?: string;
}

// One question/answer exchange in the pre-draft interview.
export interface QATurn {
  turn: number;
  question: string;
  answer: string;
}

// Mirrors backend QuestionInterviewResult (consumer-safe fields only).
// Appeal Q&A is traced and shown back to the user — never graded.
export interface QuestionInterview {
  qa_transcript: QATurn[];
  planned_questions: string[];
  patient_gap_note: string;
  skipped: boolean;
}

// Mirrors backend QuestionTurnResponse (/v1/appeal/questions/*).
export interface QuestionTurn {
  interview_id: string;
  question: string | null;
  turn: number;
  done: boolean;
  planned_questions: string[];
  patient_gap_note: string;
}

export interface QuestionStartRequest {
  denial_text: string;
  clinical_context?: string;
  /** Insurer only — denial type is never knowable a priori on appeal. */
  insurer?: string;
}

// The live /v1/appeal response.
export interface AppealResponse {
  run_id: string;
  appeal_letter: string;
  outcome: SimulatorResult;
  risk_flags: string[];
  trace_metadata: TraceMetadata;
  question_interview?: QuestionInterview | null;
}

// Plain-English "here's what we heard" — present in demo fixtures, optional live (spec §6).
export interface MirrorBlock {
  insurer: string;
  what_was_denied: string;
  why_they_said_no: string;
  deadline_note: string;       // factual, no urgency
  strongest_angle: string;
}

// Demo fixtures add the side-rail material the live API doesn't return yet.
export interface AppealFixture extends AppealResponse {
  mirror: MirrorBlock;
  citations_used: { title: string; quote: string }[];
  missing_evidence_checklist: string[];
}

// Student-safe case summary for both pickers. NO answer-key fields.
export interface CaseSummary {
  case_id: string;
  insurer: InsurerPin;
  denial_type: string;      // human label, e.g. "Medical necessity"
  headline: string;         // one calm line, e.g. "Wegovy denied as a plan exclusion"
  denial_letter_text: string;
  patient_age: number;
  patient_gender: PatientGender;
  /** Retained for showcase fixtures; not sent to the drafter on /appeal. */
  clinical_context?: string;
}

export type ShowcaseMeasureVariant = "baseline" | "candidate";

/** Drafter + simulator only — one before/after learning column. */
export interface ShowcaseMeasureResult {
  case_id: string;
  variant: ShowcaseMeasureVariant;
  verdict: Verdict;
  score: number;
  threshold: number;
  letter_excerpt: string;
  appeal_letter: string;
  outcome: SimulatorResult;
  prompt_version: string;
  risk_flags: string[];
}

// Showcase bundle for one case.
export interface ShowcaseBundle {
  case_id: string;
  measured: boolean;        // true = real recorded run; false = faithful stand-in
  v1: { composite: number; verdict: Verdict; letter_excerpt: string };
  v3: { composite: number; verdict: Verdict; letter_excerpt: string };
  lift_relative_pct: number;
  what_changed: string[];   // laundered reflection notes
  counterfactual: { on_composite: number; off_composite: number };
  phoenix_url?: string;
}

export interface ShowcaseManifest {
  benchmark_id: string;
  version: string;
  quick_slice: string;
  quick_train: CaseSummary[];
  quick_holdout: CaseSummary[];
  serious_train_count: number;
  serious_holdout: CaseSummary[];
}

export interface ShowcaseRunError {
  code: string;
  message: string;
}

export interface ShowcaseRunDiagnostics {
  stage:
    | "queued"
    | "measure_before"
    | "train_gepa"
    | "waiting_for_approval"
    | "promote"
    | "measure_after"
    | "failed"
    | "cancelled"
    | "rejected"
    | "rolled_back";
  stage_started_at?: string | null;
  stage_finished_at?: string | null;
  current_case_id?: string | null;
  completed_cases: number;
  total_cases: number;
  retryable: boolean;
  last_error?: ShowcaseRunError | null;
  phoenix_trace_ids: string[];
  cloud_log_filter: string;
}

export interface ShowcaseRunSession {
  session_id: string;
  run_type: "quick" | "serious";
  status:
    | "queued"
    | "running"
    | "needs_approval"
    | "promoted"
    | "successful"
    | "failed"
    | "cancelled"
    | "rejected"
    | "rolled_back";
  created_at: string;
  updated_at: string;
  case_ids: string[];
  diagnostics: ShowcaseRunDiagnostics;
  cancelled: boolean;
  approved_by?: string | null;
  proposal?: Record<string, unknown> | null;
  promotion_preview?: Record<string, unknown> | null;
  pre_measure_results: Record<string, unknown>[];
  training_pre_measure_results: Record<string, unknown>[];
  training_post_measure_results: Record<string, unknown>[];
  post_measure_results: Record<string, unknown>[];
  regression_detected: boolean;
  regression_summary?: string | null;
}

export interface ShowcaseRollbackFileSnapshot {
  path: string;
  exists: boolean;
  content?: string | null;
  sha256?: string | null;
}

export interface ShowcaseRollbackTarget {
  run_type: string;
  session_id: string;
  promoted_at: string;
  candidate_id: string;
  files: ShowcaseRollbackFileSnapshot[];
}
