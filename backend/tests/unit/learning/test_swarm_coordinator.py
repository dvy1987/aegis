from app.learning.benchmark_dataset import micro_benchmark_fixture
from app.learning.models import Component, ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore
from app.learning.swarm_candidate import swarm_seed_candidate
from app.learning.swarm_coordinator import SwarmLearningCoordinator
from app.learning.swarm_experiment import StubSwarmExperimentRunner

SLICE = "Cigna:medical_necessity:not_evidence_based"


def _seed_store(*, dimension: str, component_hint: str | None = None) -> InMemoryPhoenixLearningStore:
    store = InMemoryPhoenixLearningStore()
    seed = swarm_seed_candidate()
    for comp in seed.components.values():
        store.seed_component(comp)
    dims = {
        "grounding": 5,
        "appeal_vector_capture": 5,
        "case_specific_clinical_rebuttal": 5,
        "question_agent": 5,
        "persuasive_coherence": 5,
    }
    dims[dimension] = 1
    for cid in ("micro_t1", "micro_t2"):
        store.add_run(
            "benchmark_train",
            ScoredRun(
                case_id=cid,
                slice=SLICE,
                dimension_scores=dims,
                hard_gate_pass=True,
                weighted_quality=composite_score(dims, True),
                improvement_notes={dimension: f"strengthen {component_hint or dimension}"},
            ),
        )
    return store


def _coordinator(store: InMemoryPhoenixLearningStore) -> SwarmLearningCoordinator:
    return SwarmLearningCoordinator(
        store=store,
        runner=StubSwarmExperimentRunner(micro_benchmark_fixture()),
        reflection_client=StubReflectionClient(),
        slice_filter=SLICE,
        max_rounds=4,
    )


def test_swarm_coordinator_proposes_lift_for_strategist():
    store = _seed_store(dimension="appeal_vector_capture")
    result = _coordinator(store).optimize()
    assert result is not None
    assert result.proposal is not None
    assert result.resolved_component_id == "strategist"
    assert result.proposal.is_promotable
    assert result.proposal.per_dimension_deltas["appeal_vector_capture"] > 0


def test_swarm_coordinator_targets_medical_necessity_for_clinical_dim():
    store = _seed_store(dimension="case_specific_clinical_rebuttal")
    result = _coordinator(store).optimize()
    assert result is not None
    assert result.resolved_component_id == "medical_necessity"


def test_swarm_coordinator_halts_without_phoenix_signal_INV1():
    store = InMemoryPhoenixLearningStore()
    seed = swarm_seed_candidate()
    for comp in seed.components.values():
        store.seed_component(comp)
    assert _coordinator(store).optimize() is None


def test_swarm_coordinator_promote_registers_mutated_component():
    store = _seed_store(dimension="appeal_vector_capture")
    coord = _coordinator(store)
    result = coord.optimize()
    assert result and result.proposal
    coord.promote(result.proposal, approver="pm")
    versions = store.list_prompt_versions("strategist")
    assert len(versions) >= 2
