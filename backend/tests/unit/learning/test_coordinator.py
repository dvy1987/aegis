from app.learning.coordinator import LearningCoordinator
from app.learning.experiment import StubExperimentRunner
from app.learning.models import (
    Candidate,
    Component,
    ExperimentResult,
    PromotionProposal,
    ScoredRun,
    composite_score,
)
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore

SLICE = "Cigna:medical_necessity:not_evidence_based"
SLICE_2 = "Aetna:prior_authorization:visit_limit_exceeded"
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
    for cid in ("h1", "h2"):
        store.add_run("benchmark_train", ScoredRun(
            case_id=cid, slice=SLICE, dimension_scores={"appeal_vector_capture": 1, "grounding": 3},
            hard_gate_pass=True, weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
            improvement_notes={"appeal_vector_capture": "missed the specific denial flaw"},
            prompt_version="v1", run_mode="gepa_seed"))
    return store


def _coordinator(store, runner=None):
    return LearningCoordinator(
        store=store,
        runner=runner or StubExperimentRunner(DATASET),
        reflection_client=StubReflectionClient(),
        slice_filter=SLICE,
        holdout_split="benchmark_holdout",
        train_split="benchmark_train",
        max_rounds=6,
    )


def test_coordinator_seed_baseline_reuses_phoenix_without_rerunning_judges():
    store = _seeded_store()
    calls: list[tuple[str, int | None]] = []

    class _TrackingRunner(StubExperimentRunner):
        def run(self, candidate, *, dataset_split, gepa_round=None):
            calls.append((candidate.candidate_id, gepa_round))
            return super().run(candidate, dataset_split=dataset_split, gepa_round=gepa_round)

    proposal = _coordinator(store, runner=_TrackingRunner(DATASET)).optimize()
    assert proposal is not None
    assert ("seed", 0) not in calls
    assert proposal.before.experiment_id.endswith("_phoenix_baseline")


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
    for case in MULTI_SLICE_DATASET:
        store.add_run("benchmark_train", ScoredRun(
            case_id=case["case_id"], slice=case["slice"],
            dimension_scores={"appeal_vector_capture": 1, "grounding": 3},
            hard_gate_pass=True,
            weighted_quality=composite_score({"appeal_vector_capture": 1, "grounding": 3}, True),
            improvement_notes={"appeal_vector_capture": "missed the denial-specific rebuttal"},
            prompt_version="v1", run_mode="gepa_seed"))

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
    assert f"playbook:{SLICE}" in proposal.candidate.components
    assert f"playbook:{SLICE_2}" in proposal.candidate.components
    assert "geo_playbook:us" in proposal.candidate.components
    assert proposal.after.composite > proposal.before.composite


def test_coordinator_preview_mutates_drafter_question_agent_and_playbook_in_one_round():
    store = _seeded_store()
    store.seed_component(
        Component(
            component_id="question_agent_system_prompt",
            kind="prompt",
            version="v1",
            text="probe",
        )
    )
    coord = LearningCoordinator(
        store=store,
        runner=StubExperimentRunner(DATASET),
        reflection_client=StubReflectionClient(),
        slice_filter=SLICE,
        slice_filters=[SLICE],
        holdout_split="benchmark_holdout",
        train_split="benchmark_train",
        max_rounds=1,
        mutate_component_ids_per_round=[
            "drafter_system_prompt",
            "question_agent_system_prompt",
            f"playbook:{SLICE}",
            "geo_playbook:us",
        ],
    )
    proposal = coord.optimize()
    assert proposal is not None
    child = proposal.candidate
    assert child.components["drafter_system_prompt"].version != "v1"
    assert child.components["question_agent_system_prompt"].version != "v1"
    assert child.components[f"playbook:{SLICE}"].version != "v1"
    assert child.components["geo_playbook:us"].version != "cold-start"
    assert child.candidate_id == "c4"


def test_promote_skips_playbooks_outside_active_slices():
    store = InMemoryPhoenixLearningStore()
    store.seed_component(Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="draft"))
    for slice_key in (SLICE, SLICE_2):
        store.seed_component(
            Component(
                component_id=f"playbook:{slice_key}",
                kind="playbook",
                version="v1",
                playbook={"tactics": [], "dimension_targets": []},
            )
        )
    coord = LearningCoordinator(
        store=store,
        runner=StubExperimentRunner(DATASET),
        reflection_client=StubReflectionClient(),
        slice_filter=SLICE,
        slice_filters=[SLICE],
        holdout_split="benchmark_holdout",
        train_split="benchmark_train",
        max_rounds=1,
    )
    candidate = Candidate(
        candidate_id="c1",
        components={
            "drafter_system_prompt": Component(
                component_id="drafter_system_prompt",
                kind="prompt",
                version="v2",
                text="updated",
            ),
            f"playbook:{SLICE}": Component(
                component_id=f"playbook:{SLICE}",
                kind="playbook",
                version="v2",
                playbook={"tactics": ["active"], "dimension_targets": []},
            ),
            f"playbook:{SLICE_2}": Component(
                component_id=f"playbook:{SLICE_2}",
                kind="playbook",
                version="v2",
                playbook={"tactics": ["should not promote"], "dimension_targets": []},
            ),
        },
        origin="reflect",
    )
    proposal = PromotionProposal(
        candidate=candidate,
        before=ExperimentResult(candidate_id="seed", dataset_split="pre", composite=0.2),
        after=ExperimentResult(candidate_id="c1", dataset_split="post", composite=0.8),
        per_dimension_deltas={"grounding": 0.2},
        vetoes=[],
    )
    coord.promote(proposal, approver="pm")
    assert store.read_prompt_version(f"playbook:{SLICE}").version == "v2"
    assert store.read_prompt_version(f"playbook:{SLICE_2}").version == "v1"
