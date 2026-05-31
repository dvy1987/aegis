from __future__ import annotations

from typing import Any, Protocol

from app.learning.models import (
    Candidate, CaseScore, DIMENSIONS, ExperimentResult, composite_score,
)


class ExperimentRunner(Protocol):
    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult: ...


def _targeted_dimensions(candidate: Candidate, slice_: str) -> list[str]:
    """Which dimensions this candidate explicitly aims to improve, from playbook
    dimension_targets and `dim:<name>` lines in the drafter prompt."""
    targets: set[str] = set()
    pb = candidate.components.get(f"playbook:{slice_}")
    if pb and pb.playbook:
        targets |= set(pb.playbook.get("dimension_targets", []))
    prompt = candidate.components.get("drafter_system_prompt")
    if prompt and prompt.text:
        for line in prompt.text.splitlines():
            if "dim:" in line:
                targets.add(line.split("dim:")[1].strip().rstrip("."))
    return [d for d in targets if d in DIMENSIONS]


class StubExperimentRunner:
    """Deterministic offline scorer: each targeted dimension is bumped two anchor steps
    (1->3->5). Gives the Coordinator a real, monotone gradient to climb in tests."""

    name = "stub_experiment_runner"

    def __init__(self, dataset: list[dict[str, Any]]) -> None:
        self.dataset = dataset

    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult:
        per_case: list[CaseScore] = []
        for case in self.dataset:
            dims = dict(case["base"])
            for d in _targeted_dimensions(candidate, case["slice"]):
                dims[d] = min(5, dims.get(d, 1) + 2)
            comp = composite_score(dims, hard_gate_pass=True)
            per_case.append(CaseScore(case_id=case["case_id"], composite=comp,
                                      dimension_scores=dims, hard_gate_pass=True))
        mean = round(sum(c.composite for c in per_case) / len(per_case), 4) if per_case else 0.0
        return ExperimentResult(candidate_id=candidate.candidate_id, dataset_split=dataset_split,
                                per_case=per_case, composite=mean,
                                experiment_id=f"exp_{candidate.candidate_id}_{dataset_split}")


class LiveExperimentRunner:
    """Real scorer: draft each case with the candidate's components, judge it, compute the
    composite. Used by the efficacy harness (Claude/Gemini) and the GCP plan. Construction
    is offline-safe; `run` makes model calls and is exercised only with a live backend."""

    name = "live_experiment_runner"

    def __init__(self, dataset: list[dict[str, Any]], drafter_client: Any, judge_client: Any) -> None:
        self.dataset = dataset
        self.drafter_client = drafter_client
        self.judge_client = judge_client

    def run(self, candidate: Candidate, *, dataset_split: str) -> ExperimentResult:
        per_case: list[CaseScore] = []
        for case in self.dataset:
            letter = self.drafter_client.draft(
                prompt=candidate.components["drafter_system_prompt"].text or "",
                parsed_case=case["parsed_case"], citations=case.get("citations", []),
                playbook=(candidate.components.get(f"playbook:{case['slice']}").playbook
                          if candidate.components.get(f"playbook:{case['slice']}") else {}),
                phoenix_summary=case.get("phoenix_summary", {}))
            verdict = self.judge_client.score(case=case, appeal_letter=letter)  # -> dict-like
            dims = verdict["dimension_scores"]
            gate = verdict["hard_gate_pass"]
            per_case.append(CaseScore(case_id=case["case_id"], composite=composite_score(dims, gate),
                                      dimension_scores=dims, hard_gate_pass=gate,
                                      simulator_verdict=verdict.get("simulator_verdict")))
        mean = round(sum(c.composite for c in per_case) / len(per_case), 4) if per_case else 0.0
        return ExperimentResult(candidate_id=candidate.candidate_id, dataset_split=dataset_split,
                                per_case=per_case, composite=mean,
                                experiment_id=f"exp_{candidate.candidate_id}_{dataset_split}")
