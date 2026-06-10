from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _coerce_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        if "," in value:
            return [part.strip() for part in value.split(",") if part.strip()]
        return [value.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    return []


def _coerce_citation_hits(value: object) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [
            {"corpus_doc_id": doc_id, "title": doc_id, "quote": ""}
            for doc_id in _coerce_str_list(value)
        ]
    if isinstance(value, (list, tuple)):
        out: list[Any] = []
        for item in value:
            if hasattr(item, "corpus_doc_id") and hasattr(item, "quote"):
                out.append(item)
            elif isinstance(item, str):
                out.append({"corpus_doc_id": item, "title": item, "quote": ""})
            elif isinstance(item, dict):
                out.append(item)
            elif hasattr(item, "model_dump"):
                out.append(item.model_dump())
        return out
    return []


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
    patient_age: int | None = None
    patient_gender: str = ""

    @field_validator("deadlines_mentioned", "missing_facts", mode="before")
    @classmethod
    def _coerce_list_fields(cls, value: object) -> object:
        return _coerce_str_list(value)


class CitationHit(BaseModel):
    corpus_doc_id: str
    title: str
    quote: str
    relevance_score: float = 0.0


class RetrievalResult(BaseModel):
    query: str
    hits: list[CitationHit] = Field(default_factory=list)

    @field_validator("hits", mode="before")
    @classmethod
    def _coerce_hits(cls, value: object) -> object:
        return _coerce_citation_hits(value)


class PhoenixSummary(BaseModel):
    status: Literal["cold_start", "disabled", "unavailable", "available"]
    query: str
    similar_trace_count: int = 0
    failure_patterns: list[str] = Field(default_factory=list)
    success_traits: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator(
        "failure_patterns", "success_traits", "risk_flags", mode="before"
    )
    @classmethod
    def _coerce_summary_lists(cls, value: object) -> object:
        return _coerce_str_list(value)


class Playbook(BaseModel):
    insurer: str
    denial_type: str
    version: str
    status: Literal["loaded", "missing"]
    tactics: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("tactics", "required_evidence", "risk_flags", mode="before")
    @classmethod
    def _coerce_playbook_lists(cls, value: object) -> object:
        return _coerce_str_list(value)


class AppealDraft(BaseModel):
    case_summary: str
    denial_grounds_interpreted: str
    appeal_strategy: str
    appeal_letter: str
    citations_used: list[CitationHit] = Field(default_factory=list)
    missing_evidence_checklist: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    safety_disclaimer: str

    @field_validator("citations_used", mode="before")
    @classmethod
    def _coerce_citations_used(cls, value: object) -> object:
        return _coerce_citation_hits(value)

    @field_validator("missing_evidence_checklist", "risk_flags", mode="before")
    @classmethod
    def _coerce_draft_lists(cls, value: object) -> object:
        return _coerce_str_list(value)


class CitationCheck(BaseModel):
    all_citations_traceable: bool
    checked_corpus_doc_ids: list[str] = Field(default_factory=list)
    untraceable_citations: list[str] = Field(default_factory=list)

    @field_validator("checked_corpus_doc_ids", "untraceable_citations", mode="before")
    @classmethod
    def _coerce_checked_ids(cls, value: object) -> object:
        return _coerce_str_list(value)


class SelfCheckResult(BaseModel):
    hard_gate_pass: bool
    citation_check: CitationCheck
    fact_check: dict[str, Any] = Field(default_factory=dict)
    safety_check: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("risk_flags", mode="before")
    @classmethod
    def _coerce_self_check_flags(cls, value: object) -> object:
        return _coerce_str_list(value)


class FeatureMark(BaseModel):
    anchor: Literal[1, 3, 5]
    evidence: str = ""


class FeatureAssessment(BaseModel):
    """LLM output of the simulator's fuzzy step: critique-first, then per-feature
    1/3/5 anchors with evidence. No score, no verdict."""

    critique: str = ""
    features: dict[str, FeatureMark] = Field(default_factory=dict)
    # Each entry = one denial reason from the denial letter still not rebutted with
    # concrete facts in the appeal. Non-empty list triggers a hard DENY in scoring.
    unrebutted_denial_points: list[str] = Field(default_factory=list)


class FeatureScore(BaseModel):
    feature: str
    anchor: Literal[1, 3, 5]
    weight: float
    must_have: bool
    evidence: str = ""


class SimulatorResult(BaseModel):
    verdict: Literal["APPROVE", "DENY"]
    score: float                       # normalized 0.0–1.0
    threshold: float                   # e.g. 0.70
    feature_scores: list[FeatureScore] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)   # why DENY (empty on APPROVE)
    critique: str = ""
    rationale: list[str] = Field(default_factory=list)


class QATurn(BaseModel):
    """One question/answer exchange in the pre-draft interview."""

    turn: int
    question: str
    answer: str = ""


class QuestionInterviewResult(BaseModel):
    """Output of the pre-draft question agent (appeal user or showcase simulator).

    - ``enriched_context`` is the patient-knowable text handed to the drafter
      (original notes + substantive Q&A answers).
    - ``planned_questions`` are the questions the agent would ask; surfaced on the
      draft page when the user skips.
    - ``patient_gap_note`` is plain-English UX copy for the draft page (never the
      letter).
    - ``internal_gap_analysis`` is for judges/Phoenix only.
    """

    qa_transcript: list[QATurn] = Field(default_factory=list)
    enriched_context: str = ""
    planned_questions: list[str] = Field(default_factory=list)
    patient_gap_note: str = ""
    internal_gap_analysis: str = ""
    skipped: bool = False


class TraceMetadata(BaseModel):
    case_id: str
    insurer: str
    denial_type: str
    plan_type: str
    state: str
    prompt_version: str = "aegis_v1_weak"
    playbook_version: str = "cold-start"
    dataset_split: str = "interactive"
    run_mode: str = "interactive"
    search_planner_version: str = "search_planner_v1"
    library_search_query: str = ""
    library_available: bool = True
    cloud_library_used: bool = False
    discovery_enabled: bool = False
    discovery_ran: bool = False
    discovery_fetch_count: int = 0
    discovery_queries: list[str] = Field(default_factory=list)
    discovery_ingested_count: int = 0
    discovery_rejected_count: int = 0
    layer3_refinement_ran: bool = False


class AppealPackage(BaseModel):
    run_id: str
    parsed_case: ParsedCase
    appeal_package_draft: AppealDraft
    self_check: SelfCheckResult
    risk_flags: list[str] = Field(default_factory=list)
    trace_metadata: TraceMetadata
    # Pre-draft interview artifact (appeal: traced not graded; showcase: graded).
    question_interview: dict[str, Any] | None = None
