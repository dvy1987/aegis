"""Experiment runner for swarm prompt evolution (Phase 6)."""

from __future__ import annotations

from typing import Any, Protocol

from app.aegis_swarm.tools import AGENT_OWNED_DIMENSIONS
from app.learning.models import (
    Candidate, CaseScore, DIMENSIONS, ExperimentResult, composite_score,
)


class SwarmExperimentRunner(Protocol):
    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult: ...


def _changed_roles(parent: Candidate, child: Candidate) -> list[str]:
    changed: list[str] = []
    for role, comp in child.components.items():
        prev = parent.components.get(role)
        if prev is None or prev.version != comp.version:
            changed.append(role)
    return changed


def _bump_dimensions(
    candidate: Candidate,
    *,
    changed_roles: list[str],
    weakest: str | None = None,
) -> set[str]:
    """Dimensions this candidate should improve in deterministic stub scoring."""
    dims: set[str] = set(candidate.dimension_targets)
    if weakest:
        dims.add(weakest)
    for comp in candidate.components.values():
        if comp.text:
            for line in comp.text.splitlines():
                if "dim:" in line:
                    dims.add(line.split("dim:")[1].strip().rstrip("."))
    for role in changed_roles:
        dims.update(AGENT_OWNED_DIMENSIONS.get(role, []))
    return {d for d in dims if d in DIMENSIONS}


class StubSwarmExperimentRunner:
    """Offline scorer: re-run is simulated via monotone dimension bumps for the
    mutated agent's owned dimensions + explicit ``dim:`` tags from reflection."""

    name = "stub_swarm_experiment_runner"

    def __init__(self, dataset: list[dict[str, Any]]) -> None:
        self.dataset = dataset
        self._seed: Candidate | None = None

    def set_seed(self, seed: Candidate) -> None:
        self._seed = seed

    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult:
        cases = [c for c in self.dataset if c.get("dataset_split") == dataset_split]
        parent = self._seed or candidate
        changed = _changed_roles(parent, candidate) if self._seed else list(candidate.components)
        weakest = candidate.dimension_targets[0] if candidate.dimension_targets else None
        bump = _bump_dimensions(candidate, changed_roles=changed, weakest=weakest)

        per_case: list[CaseScore] = []
        for case in cases:
            dims = dict(case["base"])
            for d in bump:
                dims[d] = min(5, dims.get(d, 1) + 2)
            comp = composite_score(dims, hard_gate_pass=True)
            per_case.append(
                CaseScore(
                    case_id=case["case_id"],
                    composite=comp,
                    dimension_scores=dims,
                    hard_gate_pass=True,
                )
            )
        mean = round(sum(c.composite for c in per_case) / len(per_case), 4) if per_case else 0.0
        return ExperimentResult(
            candidate_id=candidate.candidate_id,
            dataset_split=dataset_split,
            per_case=per_case,
            composite=mean,
            experiment_id=f"swarm_exp_{candidate.candidate_id}_{dataset_split}",
        )
