from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DenialType = Literal[
    "medical_necessity",
    "prior_authorization",
    "coverage_exclusion",
    "out_of_scope",
    "unknown",
]


class ParsedCase(BaseModel):
    case_id: str
    insurer: str
    denial_type: DenialType
    plan_type: str = "commercial"
    service_or_procedure: str
    diagnosis_summary: str
    state: str = "unknown"
    cited_denial_reason: str
    deadlines_mentioned: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    denial_text: str
    clinical_context: str = ""


class CitationHit(BaseModel):
    corpus_doc_id: str
    title: str
    quote: str
    relevance_score: float = 0.0


class RetrievalResult(BaseModel):
    query: str
    hits: list[CitationHit]


class PhoenixSummary(BaseModel):
    status: Literal["cold_start", "disabled", "unavailable", "available"]
    query: str
    similar_trace_count: int = 0
    failure_patterns: list[str] = Field(default_factory=list)
    success_traits: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class Playbook(BaseModel):
    insurer: str
    denial_type: str
    version: str
    status: Literal["loaded", "missing"]
    tactics: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class AppealDraft(BaseModel):
    case_summary: str
    denial_grounds_interpreted: str
    appeal_strategy: str
    appeal_letter: str
    citations_used: list[CitationHit] = Field(default_factory=list)
    missing_evidence_checklist: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    safety_disclaimer: str


class CitationCheck(BaseModel):
    all_citations_traceable: bool
    checked_corpus_doc_ids: list[str] = Field(default_factory=list)
    untraceable_citations: list[str] = Field(default_factory=list)


class SelfCheckResult(BaseModel):
    hard_gate_pass: bool
    citation_check: CitationCheck
    fact_check: dict[str, Any] = Field(default_factory=dict)
    safety_check: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)


class SimulatorResult(BaseModel):
    verdict: Literal["APPROVE", "DENY"]
    score: int
    threshold: int
    features: dict[str, bool]
    rationale: list[str] = Field(default_factory=list)


class TraceMetadata(BaseModel):
    case_id: str
    insurer: str
    denial_type: str
    plan_type: str
    state: str
    prompt_version: str = "aegis_v1_weak"
    playbook_version: str = "cold-start"
    dataset_split: str = "interactive"
    run_mode: Literal["interactive", "benchmark", "autonomous_promotion"] = (
        "interactive"
    )


class AppealPackage(BaseModel):
    run_id: str
    parsed_case: ParsedCase
    appeal_package_draft: AppealDraft
    self_check: SelfCheckResult
    risk_flags: list[str] = Field(default_factory=list)
    trace_metadata: TraceMetadata
