from app.learning.models import Component, ScoredRun
from app.learning.store import InMemoryPhoenixLearningStore


def _run(case_id, slice_, scores, gate=True, notes=None):
    from app.learning.models import composite_score
    return ScoredRun(case_id=case_id, slice=slice_, dimension_scores=scores,
                     hard_gate_pass=gate, weighted_quality=composite_score(scores, gate),
                     improvement_notes=notes or {})


def test_store_reads_runs_filtered_by_split():
    store = InMemoryPhoenixLearningStore()
    store.add_run("benchmark_train", _run("a", "Cigna:medical_necessity", {"grounding": 1}))
    store.add_run("benchmark_holdout", _run("b", "Cigna:medical_necessity", {"grounding": 5}))
    train = store.read_scored_runs(dataset_split="benchmark_train")
    assert [r.case_id for r in train] == ["a"]


def test_store_round_trips_component_versions():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="weak"))
    cv = store.read_prompt_version("drafter_system_prompt")
    assert cv.version == "v1" and cv.text == "weak"
    assert store.list_prompt_versions("drafter_system_prompt")[0].version == "v1"


def test_register_promotion_bumps_version_and_records_audit():
    from app.learning.models import Candidate, PromotionAudit
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="weak"))
    cand = Candidate(candidate_id="c2", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", version="v2", text="better")})
    audit = PromotionAudit(candidate_id="c2", experiment_id="exp1", before_composite=0.4,
                           after_composite=0.7, per_dimension_deltas={}, diff_summary="d", approver="pm")
    store.register_promotion(cand, audit)
    assert store.read_prompt_version("drafter_system_prompt").text == "better"
    assert len(store.list_prompt_versions("drafter_system_prompt")) == 2
    assert store.audits[-1].approver == "pm"
