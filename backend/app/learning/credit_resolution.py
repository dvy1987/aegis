"""Credit-map resolution for the swarm Learning Coordinator (Phase 6).

Maps rubric dimensions to the agent prompt component that should be evolved,
with optional researcher-level override when trace signals show a corpus/retrieval
gap rather than a strategy/draft failure.

Every pipeline agent may be targeted when the map says so — the three weak-v1
agents are starting baselines only, not an exclusive evolution set.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.aegis_swarm.prompts import registry
from app.learning.models import DIMENSIONS, DIMENSION_WEIGHTS, ScoredRun

# Agents whose prompts participate in the swarm pipeline and may be evolved.
EVOLVABLE_AGENT_ROLES: tuple[str, ...] = tuple(
    role for role in registry.AGENT_ROLES if role != "orchestrator"
)

# Master-stage autonomous promotion must not rewrite safety-critical reviewers (NFR-3).
MASTER_AUTONOMY_FORBIDDEN: frozenset[str] = frozenset({"adversarial_reviewer"})

# Primary prompt owner per quality dimension (mirrors credit-assignment-map.md).
DIMENSION_PRIMARY_COMPONENT: dict[str, str] = {
    "grounding": "drafter",
    "appeal_vector_capture": "strategist",
    "case_specific_clinical_rebuttal": "medical_necessity",
    "evidence_completeness": "strategist",
    "persuasive_coherence": "drafter",
}

# Dimensions where a thin corpus is a plausible root cause (ADR-007).
CORPUS_GAP_PLAUSIBLE: frozenset[str] = frozenset({
    "grounding",
    "case_specific_clinical_rebuttal",
    "evidence_completeness",
})

# Map empty-retrieval risk flags to the researcher role that reported them.
_EMPTY_FLAG_TO_RESEARCHER: dict[str, str] = {
    "no_guidelines_found": "medical_necessity",
    "no_statute_found": "legal_researcher",
    "cpb_not_found": "policy_detective",
    "no_precedent_found": "precedent_miner",
    "no_trace_history": "insurer_intelligence",
}

ResearcherRole = Literal[
    "medical_necessity",
    "legal_researcher",
    "policy_detective",
    "precedent_miner",
    "insurer_intelligence",
]


class CreditResolution(BaseModel):
    """Outcome of routing a weak dimension to an action."""

    weakest_dimension: str
    action: Literal["evolve_prompt", "corpus_gap"]
    component_id: str = ""
    corpus_gap_reason: str = ""
    researcher_override: bool = False


def weighted_dimension_means(runs: list[ScoredRun]) -> dict[str, float]:
    if not runs:
        return {d: 0.0 for d in DIMENSIONS}
    present = {d for r in runs for d in r.dimension_scores}
    scored = present or set(DIMENSIONS)
    return {
        d: sum(r.dimension_scores.get(d, 3) for r in runs) / len(runs) for d in scored
    }


def pick_weakest_dimension(dim_means: dict[str, float]) -> str:
    """Lowest mean anchor, tie-broken by highest business weight."""
    pool = [d for d in DIMENSIONS if d in dim_means]
    if not pool:
        pool = list(DIMENSIONS)

    def sort_key(d: str) -> tuple[float, float]:
        return (dim_means.get(d, 5.0), -DIMENSION_WEIGHTS[d])

    return min(pool, key=sort_key)


def _failing_runs(runs: list[ScoredRun], dimension: str) -> list[ScoredRun]:
    return [
        r for r in runs
        if not r.hard_gate_pass or r.dimension_scores.get(dimension, 5) < 5
    ]


_DIMENSION_RESEARCHERS: dict[str, tuple[str, ...]] = {
    "grounding": ("medical_necessity", "legal_researcher", "policy_detective"),
    "case_specific_clinical_rebuttal": ("medical_necessity",),
    "evidence_completeness": ("policy_detective", "medical_necessity"),
}


def _researcher_from_trace_signals(signals: list[dict], dimension: str) -> str | None:
    """Single empty researcher for this dimension -> evolve that researcher; else corpus gap."""
    allowed = _DIMENSION_RESEARCHERS.get(dimension, ())
    empty_roles: list[str] = []
    for sig in signals:
        role = sig.get("role", "")
        if role not in allowed:
            continue
        status = sig.get("status", "full")
        if status not in {"empty", "partial"}:
            continue
        flags = sig.get("risk_flags") or []
        if any(f in _EMPTY_FLAG_TO_RESEARCHER for f in flags):
            empty_roles.append(role)
    unique = sorted(set(empty_roles))
    if len(unique) == 1:
        return unique[0]
    return None


def _aggregate_trace_signals(runs: list[ScoredRun]) -> list[dict]:
    out: list[dict] = []
    for run in runs:
        out.extend(run.swarm_trace_signals or [])
    return out


def resolve_credit_target(runs: list[ScoredRun]) -> CreditResolution:
    """Apply the credit-assignment-map resolution algorithm to train-split runs."""
    dim_means = weighted_dimension_means(runs)
    weakest = pick_weakest_dimension(dim_means)
    primary = DIMENSION_PRIMARY_COMPONENT[weakest]
    failing = _failing_runs(runs, weakest) or runs
    signals = _aggregate_trace_signals(failing)

    if weakest in CORPUS_GAP_PLAUSIBLE:
        researcher = _researcher_from_trace_signals(signals, weakest)
        if researcher is not None:
            return CreditResolution(
                weakest_dimension=weakest,
                action="evolve_prompt",
                component_id=researcher,
                researcher_override=True,
            )
        gap_flags = sum(
            1 for sig in signals
            if sig.get("status") in {"empty", "partial"}
            or any(f in _EMPTY_FLAG_TO_RESEARCHER for f in (sig.get("risk_flags") or []))
        )
        if gap_flags >= max(1, len(signals) // 2):
            return CreditResolution(
                weakest_dimension=weakest,
                action="corpus_gap",
                corpus_gap_reason=(
                    f"retrieval gaps dominate for {weakest} "
                    f"({gap_flags}/{max(len(signals), 1)} trace signals)"
                ),
            )

    component_id = primary
    if component_id not in EVOLVABLE_AGENT_ROLES:
        component_id = "drafter"

    return CreditResolution(
        weakest_dimension=weakest,
        action="evolve_prompt",
        component_id=component_id,
    )


def assert_evolvable(component_id: str) -> None:
    if component_id not in EVOLVABLE_AGENT_ROLES:
        raise ValueError(f"component {component_id!r} is not an evolvable swarm agent role")
