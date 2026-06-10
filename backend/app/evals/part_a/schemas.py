from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GateVerdict = Literal["PASS", "FAIL"]
AnchorScore = Literal[1, 3, 5]
JudgeScore = Literal[1, 2, 3, 4, 5, "PASS", "FAIL"]


CANONICAL_DISCLAIMER = "Not legal or medical advice. Draft assistance only."


class StudentCasePacket(BaseModel):
    """Case fields visible to the runtime appeal agent."""

    case_id: str
    denial_letter_text: str
    clinical_context: str


class CorpusExcerpt(BaseModel):
    corpus_doc_id: str
    title: str = ""
    quote: str


class TeacherGradingPacket(BaseModel):
    """Teacher-only answer key for quality judges."""

    case_id: str
    insurer: str
    denial_type: str
    patient_profile: dict[str, Any] = Field(default_factory=dict)
    denial_letter_text: str
    clinical_context: str
    matrix_cell: dict[str, Any] = Field(default_factory=dict)
    denial_pattern_sources: list[str] = Field(default_factory=list)
    denial_letter_references: list[dict[str, Any]] = Field(default_factory=list)
    expected_appeal_vectors: list[str] = Field(default_factory=list)
    exploitable_weaknesses: list[str] = Field(default_factory=list)
    strong_defenses: list[str] = Field(default_factory=list)
    submission_timestamp: str | None = None
    denial_timestamp: str | None = None
    corpus_excerpts: list[CorpusExcerpt] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class JudgeResult(BaseModel):
    dimension: str
    reasoning: str
    score: JudgeScore
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_quotes: list[str] = Field(default_factory=list)
    improvement: str | None = None


class PanelReport(BaseModel):
    case_id: str
    verdict: GateVerdict
    weighted_quality: float | None
    hard_gate_failures: list[str] = Field(default_factory=list)
    promotion_blockers: list[str] = Field(default_factory=list)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    judge_results: dict[str, JudgeResult]
    weights: dict[str, float]
    risk_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
