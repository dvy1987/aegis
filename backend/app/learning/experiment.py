from __future__ import annotations

from typing import Any, Protocol

from app.evals.part_a.evaluated_run import run_evaluated_case as _run_evaluated_case
from app.learning.models import (
    Candidate,
    CaseScore,
    DIMENSIONS,
    ExperimentResult,
    ScoredRun,
    composite_score,
    normalize_dimension_scores,
)
from app.learning.store import PhoenixLearningStore

SEED_BASELINE_RUN_MODES = frozenset({"", "gepa_seed"})


def _dedupe_scored_runs_by_case(runs: list[ScoredRun]) -> list[ScoredRun]:
    by_case: dict[str, ScoredRun] = {}
    for run in runs:
        by_case[run.case_id] = run
    return list(by_case.values())


def experiment_result_from_scored_runs(
    candidate_id: str,
    dataset_split: str,
    runs: list[ScoredRun],
    *,
    experiment_id: str | None = None,
) -> ExperimentResult:
    """Build an ExperimentResult from Phoenix seed annotations (no re-judging)."""
    per_case: list[CaseScore] = []
    for run in runs:
        dims = normalize_dimension_scores(run.dimension_scores)
        per_case.append(
            CaseScore(
                case_id=run.case_id,
                composite=composite_score(dims, run.hard_gate_pass),
                dimension_scores=dims,
                hard_gate_pass=run.hard_gate_pass,
                simulator_verdict=run.simulator_verdict,
            )
        )
    mean = round(sum(c.composite for c in per_case) / len(per_case), 4) if per_case else 0.0
    return ExperimentResult(
        candidate_id=candidate_id,
        dataset_split=dataset_split,
        per_case=per_case,
        composite=mean,
        experiment_id=experiment_id or f"exp_{candidate_id}_{dataset_split}_phoenix_baseline",
    )


def baseline_experiment_from_phoenix(
    store: PhoenixLearningStore,
    seed: Candidate,
    *,
    train_split: str,
    dataset_split: str,
) -> ExperimentResult | None:
    """Reuse training-seed judge annotations as the GEPA baseline (collapse pass 1+2)."""
    prompt_version = seed.components["drafter_system_prompt"].version
    runs = store.read_scored_runs(
        dataset_split=train_split,
        prompt_version=prompt_version,
    )
    if not runs:
        runs = store.read_scored_runs(dataset_split=train_split)
    seed_runs = [r for r in runs if r.run_mode in SEED_BASELINE_RUN_MODES]
    if not seed_runs:
        seed_runs = list(runs)
    seed_runs = _dedupe_scored_runs_by_case(seed_runs)
    if not seed_runs:
        return None
    return experiment_result_from_scored_runs(
        seed.candidate_id,
        dataset_split,
        seed_runs,
    )


class ExperimentRunner(Protocol):
    def run(
        self,
        candidate: Candidate,
        *,
        dataset_split: str,
        gepa_round: int | None = None,
    ) -> ExperimentResult: ...


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


def _case_obj(case: dict[str, Any], dataset_split: str) -> dict[str, Any]:
    teacher = case.get("_teacher_case")
    if isinstance(teacher, dict):
        obj = dict(teacher)
        obj["dataset_split"] = dataset_split
        return obj
    return {
        "case_id": case["case_id"],
        "denial_letter_text": case.get("denial_letter_text", ""),
        "clinical_context": case.get("clinical_context", ""),
        "dataset_split": dataset_split,
    }


class StubExperimentRunner:
    """Deterministic offline scorer: each targeted dimension is bumped two anchor steps
    (1->3->5). Gives the Coordinator a real, monotone gradient to climb in tests."""

    name = "stub_experiment_runner"

    def __init__(self, dataset: list[dict[str, Any]]) -> None:
        self.dataset = dataset

    def run(
        self,
        candidate: Candidate,
        *,
        dataset_split: str,
        gepa_round: int | None = None,
    ) -> ExperimentResult:
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
    """Real scorer: draft each case with the candidate's components via ADK pipeline,
    judge it, persist tier-B Phoenix annotations when a recorder is wired."""

    name = "live_experiment_runner"

    def __init__(
        self,
        dataset: list[dict[str, Any]],
        judge_client: Any,
        *,
        drafter_client: Any | None = None,
        recorder: Any | None = None,
        memory_eligible: bool = False,
        run_mode: str = "gepa_optimize_candidate",
    ) -> None:
        self.dataset = dataset
        self.drafter_client = drafter_client
        self.judge_client = judge_client
        self.recorder = recorder
        self.memory_eligible = memory_eligible
        self.run_mode = run_mode

    def run(
        self,
        candidate: Candidate,
        *,
        dataset_split: str,
        gepa_round: int | None = None,
    ) -> ExperimentResult:
        per_case: list[CaseScore] = []
        prompt_comp = candidate.components["drafter_system_prompt"]
        for index, case in enumerate(self.dataset):
            if index > 0:
                from app import gemini_retry

                gemini_retry.pace_gemini_call()
            pb_comp = candidate.components.get(f"playbook:{case['slice']}")
            playbook_override = pb_comp.playbook if pb_comp and pb_comp.playbook else None
            if self.recorder is not None and self.drafter_client is None:
                evaluated = _run_evaluated_case(
                    _case_obj(case, dataset_split),
                    recorder=self.recorder,
                    drafter_client=None,
                    judge_client=self.judge_client,
                    run_simulator=False,
                    drafter_prompt_version=prompt_comp.version,
                    drafter_prompt_text=prompt_comp.text,
                    playbook_override=playbook_override,
                    run_mode=self.run_mode,
                    trace_tags={
                        "memory_eligible": "true" if self.memory_eligible else "false",
                        "candidate_id": candidate.candidate_id,
                        "gepa_round": gepa_round,
                        "run_mode": self.run_mode,
                        "dataset_split": dataset_split,
                        "prompt_version": prompt_comp.version,
                    },
                )
                report = evaluated.panel_report
                dims = dict(report.dimension_scores)
                gate = report.verdict == "PASS"
            elif self.drafter_client is not None:
                letter = self.drafter_client.draft(
                    prompt=prompt_comp.text or "",
                    parsed_case=case["parsed_case"],
                    citations=case.get("citations", []),
                    playbook=playbook_override or {},
                    phoenix_summary=case.get("phoenix_summary", {}),
                )
                verdict = self.judge_client.score(case=case, appeal_letter=letter)
                dims = verdict["dimension_scores"]
                gate = verdict["hard_gate_pass"]
            else:
                raise ValueError("LiveExperimentRunner requires recorder or drafter_client")
            per_case.append(
                CaseScore(
                    case_id=case["case_id"],
                    composite=composite_score(dims, gate),
                    dimension_scores=dims,
                    hard_gate_pass=gate,
                )
            )
        mean = round(sum(c.composite for c in per_case) / len(per_case), 4) if per_case else 0.0
        return ExperimentResult(
            candidate_id=candidate.candidate_id,
            dataset_split=dataset_split,
            per_case=per_case,
            composite=mean,
            experiment_id=f"exp_{candidate.candidate_id}_{dataset_split}",
        )
