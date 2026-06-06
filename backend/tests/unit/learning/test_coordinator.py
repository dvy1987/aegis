from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import StubExperimentRunner
from app.learning.models import Component, ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore

SLICE = "Cigna:medical_necessity"
SLICE_2 = "Aetna:prior_authorization"
DATASET = [
    {"case_id": "h1", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}},
    {"case_id": "h2", "slice": SLICE, "base": {"appeal_vector_capture": 1, "grounding": 3}},
]
MULTI_SLICE_DATASET = DATASET + [
    {"case_id": "h3", "slice": SLICE_2, "base": {"appeal_vector_capture": 1, "grounding": 3}},
    {"case_id": "h4", "slice": SLICE_2, "base": {"appeal_vector_capture": 1, "grounding": 3}},
]


def _seeded_store():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    store.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    for cid in ("t1", "t2"):
        store.add_run("benchmark_train", ScoredRun(
            case_id=cid, slice=SLICE, dimension_scores={"appeal_vector_capture": 1, "grounding": 3},
            hard_gate_pass=True, weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
            improvement_notes={"appeal_vector_capture": "missed the specific denial flaw"}))
    return store


def _coordinator(store):
    return LearningCoordinator(
        store=store, runner=StubExperimentRunner(DATASET), reflection_client=StubReflectionClient(),
        slice_filter=SLICE, holdout_split="benchmark_holdout", train_split="benchmark_train",
        max_rounds=6)


def test_coordinator_proposes_a_promotable_lift():
    proposal = _coordinator(_seeded_store()).optimize()
    assert proposal.after.composite > proposal.before.composite
    assert proposal.is_promotable
    assert proposal.per_dimension_deltas["appeal_vector_capture"] > 0
    assert proposal.candidate.dimension_targets   # credit assignment recorded


def test_coordinator_halts_without_phoenix_signal_INV1():
    empty = InMemoryPhoenixLearningStore()
    empty.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    empty.seed_component(Component(component_id=f"playbook:{SLICE}", kind="playbook", version="v1",
                                   playbook={"tactics": [], "dimension_targets": []}))
    proposal = _coordinator(empty).optimize()   # no runs recorded -> no gradient
    assert proposal is None   # INV-1: disable Phoenix signal -> learning halts


def test_promote_writes_new_version_and_audit():
    store = _seeded_store()
    coord = _coordinator(store)
    proposal = coord.optimize()
    coord.promote(proposal, approver="pm")
    # the loop improves the global drafter prompt first; only changed components get a new version
    assert len(store.list_prompt_versions("drafter_system_prompt")) == 2
    assert store.read_prompt_version("drafter_system_prompt").version != "v1"
    assert store.audits[-1].after_composite == proposal.after.composite


def test_coordinator_can_seed_and_optimize_multiple_playbook_slices():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    for slice_key in (SLICE, SLICE_2):
        store.seed_component(Component(component_id=f"playbook:{slice_key}", kind="playbook", version="v1",
                                       playbook={"tactics": [], "dimension_targets": []}))
        store.add_run("benchmark_train", ScoredRun(
            case_id=f"train_{slice_key}", slice=slice_key,
            dimension_scores={"appeal_vector_capture": 1, "grounding": 3},
            hard_gate_pass=True,
            weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
            improvement_notes={"appeal_vector_capture": "missed the denial-specific rebuttal"}))

    coord = LearningCoordinator(
        store=store,
        runner=StubExperimentRunner(MULTI_SLICE_DATASET),
        reflection_client=StubReflectionClient(),
        slice_filter=SLICE,
        slice_filters=[SLICE, SLICE_2],
        holdout_split="benchmark_holdout",
        train_split="benchmark_train",
        max_rounds=4,
    )

    proposal = coord.optimize()

    assert proposal is not None
    assert set(proposal.candidate.components) == {
        "drafter_system_prompt",
        f"playbook:{SLICE}",
        f"playbook:{SLICE_2}",
    }
    assert proposal.after.composite > proposal.before.composite
