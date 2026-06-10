from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DIMENSIONS = [
    "grounding",
    "appeal_vector_capture",
    "case_specific_clinical_rebuttal",
    "question_agent",
    "persuasive_coherence",
]
DIMENSION_WEIGHTS = {
    "grounding": 0.25,
    "appeal_vector_capture": 0.35,
    "case_specific_clinical_rebuttal": 0.20,
    "question_agent": 0.10,
    "persuasive_coherence": 0.10,
}


def normalize_dimension_scores(dimension_scores: dict[str, int]) -> dict[str, int]:
    """Map legacy evidence_completeness judgments to the question-agent stub score."""
    scores = {str(k): int(v) for k, v in dimension_scores.items()}
    if "evidence_completeness" in scores:
        scores.pop("evidence_completeness")
        scores.setdefault("question_agent", 5)
    return scores


def composite_score(dimension_scores: dict[str, int], hard_gate_pass: bool) -> float:
    """Weighted, hard-gated quality composite in [0.0, 1.0]. Hard-gate FAIL → 0.0;
    missing dimensions default to anchor 1; all-5 → 1.0, all-1 → 0.2."""
    if not hard_gate_pass:
        return 0.0
    scores = normalize_dimension_scores(dimension_scores)
    total = sum(DIMENSION_WEIGHTS[d] * (scores.get(d, 1) / 5.0) for d in DIMENSIONS)
    return round(total, 4)


class Component(BaseModel):
    component_id: str                       # "drafter_system_prompt" | "playbook:Cigna:medical_necessity"
    kind: Literal["prompt", "playbook"]
    version: str = "v1"
    text: str | None = None                 # kind == "prompt"
    playbook: dict | None = None            # kind == "playbook"


class Candidate(BaseModel):
    candidate_id: str
    parent_id: str | None = None
    components: dict[str, Component]
    origin: Literal["seed", "reflect", "merge", "restart"] = "seed"
    dimension_targets: list[str] = Field(default_factory=list)
    diff_summary: str = ""


class ScoredRun(BaseModel):
    """A past run read back from Phoenix, joined with its judge annotations.
    Carries ONLY laundered fields — never answer-key provenance (INV-2)."""
    case_id: str
    slice: str                              # f"{insurer}:{denial_type}"
    dimension_scores: dict[str, int]
    hard_gate_pass: bool
    weighted_quality: float
    improvement_notes: dict[str, str] = Field(default_factory=dict)  # laundered, per dimension
    simulator_verdict: Literal["APPROVE", "DENY"] | None = None
    prompt_version: str = ""
    playbook_version: str = ""
    run_mode: str = ""
    # Firewall-safe per-agent trace snapshots (role, status, risk_flags, counts only).
    swarm_trace_signals: list[dict[str, Any]] = Field(default_factory=list)


class DimensionSignal(BaseModel):
    component_id: str
    weakest_dimension: str
    failing_cases: list[ScoredRun] = Field(default_factory=list)
    notes: dict[str, list[str]] = Field(default_factory=dict)  # dimension -> laundered notes


class ComponentVersion(BaseModel):
    component_id: str
    version: str
    text: str | None = None
    playbook: dict | None = None


class CaseScore(BaseModel):
    case_id: str
    composite: float
    dimension_scores: dict[str, int]
    hard_gate_pass: bool
    simulator_verdict: Literal["APPROVE", "DENY"] | None = None


class ExperimentResult(BaseModel):
    candidate_id: str
    dataset_split: str
    per_case: list[CaseScore] = Field(default_factory=list)
    composite: float = 0.0
    experiment_id: str = ""

    def dimension_means(self) -> dict[str, float]:
        if not self.per_case:
            return {d: 0.0 for d in DIMENSIONS}
        return {
            d: round(sum(c.dimension_scores.get(d, 1) for c in self.per_case) / len(self.per_case), 4)
            for d in DIMENSIONS
        }


class PromotionAudit(BaseModel):
    candidate_id: str
    experiment_id: str
    before_composite: float
    after_composite: float
    per_dimension_deltas: dict[str, float]
    diff_summary: str
    approver: str
    vetoes: list[str] = Field(default_factory=list)


class PromotionProposal(BaseModel):
    candidate: Candidate
    before: ExperimentResult
    after: ExperimentResult
    per_dimension_deltas: dict[str, float]
    vetoes: list[str] = Field(default_factory=list)

    @property
    def is_promotable(self) -> bool:
        return not self.vetoes and self.after.composite > self.before.composite


class CorpusGapRecommendation(BaseModel):
    """When retrieval gaps dominate, queue discovery instead of prompt mutation."""

    weakest_dimension: str
    reason: str
