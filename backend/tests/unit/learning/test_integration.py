"""End-to-end offline: seed weak components + recorded signal -> optimize -> promotable
lift -> promote -> the store now serves the improved version. No GCP, no API key."""
from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import StubExperimentRunner
from app.learning.models import Component, ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore

SLICE = "Aetna:prior_authorization"
HOLDOUT = [
    {"case_id": "h1", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}},
    {"case_id": "h2", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}},
]


def test_full_offline_learning_loop():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="Draft an appeal."))
    store.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    for cid in ("h1", "h2"):
        store.add_run("benchmark_train", ScoredRun(
            case_id=cid, slice=SLICE,
            dimension_scores={"appeal_vector_capture": 1, "grounding": 3, "question_agent": 5},
            hard_gate_pass=True,
            weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3, "question_agent": 5}, True),
            improvement_notes={"appeal_vector_capture": "did not rebut the specific defect",
                               "grounding": "thin authority citations"},
            prompt_version="v1", run_mode="gepa_seed"))

    coord = LearningCoordinator(store=store, runner=StubExperimentRunner(HOLDOUT),
                                reflection_client=StubReflectionClient(), slice_filter=SLICE, max_rounds=8)
    proposal = coord.optimize()
    assert proposal is not None and proposal.is_promotable
    assert proposal.after.composite > proposal.before.composite
    assert proposal.vetoes == []

    coord.promote(proposal, approver="pm")
    promoted = store.read_prompt_version("drafter_system_prompt")
    assert promoted.version != "v1"                       # a new version was registered
    assert store.audits[-1].after_composite == proposal.after.composite
