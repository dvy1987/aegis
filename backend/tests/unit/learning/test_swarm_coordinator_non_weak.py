"""Non-weak agents must be eligible mutation targets when credit map says so."""

from app.learning.models import ScoredRun, composite_score
from app.learning.reflection_client import StubReflectionClient
from app.learning.store import InMemoryPhoenixLearningStore
from app.learning.swarm_candidate import swarm_seed_candidate
from app.learning.swarm_coordinator import SwarmLearningCoordinator
from app.learning.swarm_experiment import StubSwarmExperimentRunner

from app.learning.benchmark_dataset import micro_benchmark_fixture

SLICE = "Cigna:medical_necessity:not_evidence_based"


def _store_with_researcher_gap() -> InMemoryPhoenixLearningStore:
    store = InMemoryPhoenixLearningStore()
    seed = swarm_seed_candidate()
    for comp in seed.components.values():
        store.seed_component(comp)
    dims = {d: 5 for d in [
        "grounding", "appeal_vector_capture", "case_specific_clinical_rebuttal",
        "question_agent", "persuasive_coherence",
    ]}
    dims["grounding"] = 1
    trace = [{
        "role": "policy_detective",
        "status": "empty",
        "risk_flags": ["cpb_not_found"],
    }]
    store.add_run(
        "benchmark_train",
        ScoredRun(
            case_id="micro_t1",
            slice=SLICE,
            dimension_scores=dims,
            hard_gate_pass=True,
            weighted_quality=composite_score(dims, True),
            improvement_notes={"appeal_vector_capture": "wrong archetype"},
            swarm_trace_signals=trace,
        ),
    )
    store.add_run(
        "benchmark_train",
        ScoredRun(
            case_id="micro_t2",
            slice=SLICE,
            dimension_scores=dims,
            hard_gate_pass=True,
            weighted_quality=composite_score(dims, True),
            improvement_notes={"appeal_vector_capture": "wrong archetype"},
            swarm_trace_signals=trace,
        ),
    )
    return store


def test_policy_detective_can_be_mutation_target():
    store = _store_with_researcher_gap()
    coord = SwarmLearningCoordinator(
        store=store,
        runner=StubSwarmExperimentRunner(micro_benchmark_fixture()),
        reflection_client=StubReflectionClient(),
        slice_filter=SLICE,
        max_rounds=2,
    )
    result = coord.optimize()
    assert result is not None
    assert result.resolved_component_id == "policy_detective"
    assert result.proposal is not None
