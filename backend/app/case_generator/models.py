from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Verdict = Literal["PASS", "FAIL"]
Anchor = Literal[1, 3, 5]


class MatrixCell(BaseModel):
    insurer: str
    denial_type: str
    specialty: str
    patient_age_band: str
    patient_gender: str
    sub_tactic: str


class PatientProfile(BaseModel):
    age: int = Field(ge=18, le=89)
    gender: Literal["M", "F", "nonbinary"]
    diagnosis: str
    treatment_requested: str


class AppealDifficulty(BaseModel):
    score: int = Field(ge=1, le=5)
    reasoning: str
    exploitable_weaknesses: list[str]
    strong_defenses: list[str]

class EvaluatorDisagreement(BaseModel):
    dimension: str
    internal_verdict: str
    gumloop_verdict: str
    resolution: str

class SynthProvenance(BaseModel):
    generator_model: str
    run_id: str
    generated_at: str
    matrix_cell: MatrixCell
    prompt_versions: dict[str, str]
    banned_topic_filter_version: str
    schema_version: str
    diversity_matrix_version: str
    critic_verdicts: dict[str, Any]
    human_summary: str
    appeal_difficulty: AppealDifficulty
    evaluator_disagreements: list[EvaluatorDisagreement] = Field(default_factory=list)


class CaseDraft(BaseModel):
    case_id: str
    insurer: Literal["Aetna", "Cigna", "UHC"]
    denial_type: Literal["Medical Necessity", "Prior Authorization"]
    patient_profile: PatientProfile
    denial_pattern_sources: list[str] = Field(default_factory=list)
    denial_letter_text: str
    clinical_context: str
    synthetic_provenance: SynthProvenance


class ScenarioBrief(BaseModel):
    """Producer-1 output."""

    matrix_cell: MatrixCell
    diagnosis: str = Field(description="Specific diagnosis with ICD-10 if natural.")
    treatment_requested: str = Field(
        description="Specific procedure / drug / level of care."
    )
    denial_rationale_seed: str = Field(
        description=(
            "One paragraph laying out the insurer's likely denial rationale for "
            "this sub_tactic, in plain language. Used to seed the denial letter."
        )
    )
    rebuttal_seed: str = Field(
        description="One paragraph laying out the clinical/regulatory rebuttal direction."
    )
    patient_age: int
    patient_gender: Literal["M", "F", "nonbinary"]
    employer_archetype: str | None = Field(
        default=None,
        description="Required if patient_age_band == 71+; commercial plan justification.",
    )


class DenialLetterDraft(BaseModel):
    """Producer-2 output."""

    denial_letter_text: str


class ClinicalContextDraft(BaseModel):
    """Producer-3 output."""

    clinical_context: str


class AdversarialPerturbation(BaseModel):
    """Producer-4 output. May modify any earlier field to improve diversity."""

    denial_letter_text: str
    clinical_context: str
    diagnosis: str
    treatment_requested: str
    perturbation_notes: str


class CriticOutput(BaseModel):
    """Standard AlphaEval critic schema."""

    dimension: str
    reasoning: str
    score: Anchor | Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_quotes: list[str] = Field(default_factory=list)
    improvement: str | None = None


class StageResult(BaseModel):
    stage: str
    producer_output: dict[str, Any]
    critic_outputs: dict[str, CriticOutput]
    revisions_used: int
    passed: bool
    discard_reason: str | None = None


class RunContext(BaseModel):
    run_id: str
    generator_model: str
    generated_at: datetime
    diversity_matrix_version: str
    banned_topic_filter_version: str
    schema_version: str
