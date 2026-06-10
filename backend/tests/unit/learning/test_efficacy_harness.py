import pytest

from app.learning.efficacy_harness import EfficacyReport, run_efficacy
from app.learning.experiment import StubExperimentRunner
from app.learning.models import Component, ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore

SLICE = "Cigna:medical_necessity:not_evidence_based"
HOLDOUT = [{"case_id": "h1", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}}]


def _store():
    s = InMemoryPhoenixLearningStore()
    s.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    s.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                              playbook={"tactics": [], "dimension_targets": []}))
    s.add_run("benchmark_train", ScoredRun(case_id="t1", slice=SLICE,
              dimension_scores={"appeal_vector_capture": 1, "grounding": 3}, hard_gate_pass=True,
              weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
              improvement_notes={"appeal_vector_capture": "missed the flaw"}))
    return s


def test_harness_reports_real_held_out_lift():
    report = run_efficacy(store=_store(), runner=StubExperimentRunner(HOLDOUT),
                          reflection_client=StubReflectionClient(), slice_filter=SLICE)
    assert isinstance(report, EfficacyReport)
    assert report.lift > 0
    assert report.optimized_composite > report.baseline_composite
    assert report.dataset_split == "benchmark_holdout"


def test_harness_refuses_to_measure_on_train_split_INV_V2_3():
    with pytest.raises(ValueError):
        run_efficacy(store=_store(), runner=StubExperimentRunner(HOLDOUT),
                     reflection_client=StubReflectionClient(), slice_filter=SLICE,
                     holdout_split="benchmark_train")
