from __future__ import annotations

from pydantic import BaseModel, Field

from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import ExperimentRunner
from app.learning.reflection_client import ReflectionClient
from app.learning.store import PhoenixLearningStore


class EfficacyReport(BaseModel):
    slice_filter: str
    dataset_split: str
    baseline_composite: float
    optimized_composite: float
    lift: float
    per_dimension_deltas: dict[str, float] = Field(default_factory=dict)
    promoted_diff: str = ""
    vetoes: list[str] = Field(default_factory=list)


def run_efficacy(*, store: PhoenixLearningStore, runner: ExperimentRunner,
                 reflection_client: ReflectionClient, slice_filter: str,
                 holdout_split: str = "benchmark_holdout", train_split: str = "benchmark_train",
                 max_rounds: int = 8) -> EfficacyReport:
    """Run the full learn-loop with the injected intelligence and report held-out lift.
    Backend-agnostic: Stub (mechanics), Anthropic/Claude or Gemini (real efficacy).
    V2-INV-3: efficacy must be measured on a held-out split the reflection never trained on."""
    if holdout_split == train_split:
        raise ValueError("V2-INV-3: efficacy must be measured on a held-out split, not the train split")

    coordinator = LearningCoordinator(
        store=store, runner=runner, reflection_client=reflection_client, slice_filter=slice_filter,
        holdout_split=holdout_split, train_split=train_split, max_rounds=max_rounds)
    proposal = coordinator.optimize()
    if proposal is None:
        return EfficacyReport(slice_filter=slice_filter, dataset_split=holdout_split,
                              baseline_composite=0.0, optimized_composite=0.0, lift=0.0,
                              vetoes=["no_phoenix_signal"])
    return EfficacyReport(
        slice_filter=slice_filter, dataset_split=holdout_split,
        baseline_composite=proposal.before.composite, optimized_composite=proposal.after.composite,
        lift=round(proposal.after.composite - proposal.before.composite, 4),
        per_dimension_deltas=proposal.per_dimension_deltas, promoted_diff=proposal.candidate.diff_summary,
        vetoes=proposal.vetoes)


def _main() -> None:  # pragma: no cover - thin CLI wrapper
    """CLI entry: `python -m app.learning.efficacy_harness`. The companion GCP/efficacy
    plan wires real backends (Anthropic/Gemini drafter+judge+reflection) here; offline
    this prints a stub-backed mechanics run."""
    import json

    from app.learning.experiment import StubExperimentRunner
    from app.learning.models import Component, ScoredRun, composite_score
    from app.learning.reflection_client import StubReflectionClient
    from app.learning.store import InMemoryPhoenixLearningStore

    slice_ = "Cigna:medical_necessity:not_evidence_based"
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    store.seed_component(Component(component_id=f"playbook:{slice_}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    store.add_run("benchmark_train", ScoredRun(case_id="t1", slice=slice_,
                  dimension_scores={"appeal_vector_capture": 1, "grounding": 3}, hard_gate_pass=True,
                  weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
                  improvement_notes={"appeal_vector_capture": "missed the flaw"}))
    holdout = [{"case_id": "h1", "slice": slice_, "base": {"appeal_vector_capture": 1, "grounding": 3}}]
    report = run_efficacy(store=store, runner=StubExperimentRunner(holdout),
                          reflection_client=StubReflectionClient(), slice_filter=slice_)
    print(json.dumps(report.model_dump(), indent=2))


if __name__ == "__main__":  # pragma: no cover
    _main()
