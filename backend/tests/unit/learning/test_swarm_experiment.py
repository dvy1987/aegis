from app.learning.benchmark_dataset import micro_benchmark_fixture
from app.learning.swarm_candidate import swarm_seed_candidate
from app.learning.swarm_experiment import StubSwarmExperimentRunner
from app.learning.mutation import reflective_mutate
from app.learning.models import DimensionSignal, ScoredRun
from app.learning.reflection_client import StubReflectionClient


def test_stub_swarm_runner_monotone_lift_on_strategist_mutation():
    dataset = micro_benchmark_fixture()
    runner = StubSwarmExperimentRunner(dataset)
    seed = swarm_seed_candidate()
    runner.set_seed(seed)
    seed_score = runner.run(seed, dataset_split="benchmark_holdout").composite

    signal = DimensionSignal(
        component_id="strategist",
        weakest_dimension="appeal_vector_capture",
        failing_cases=[
            ScoredRun(
                case_id="micro_t1",
                slice="Cigna:medical_necessity",
                dimension_scores={"appeal_vector_capture": 1},
                hard_gate_pass=True,
                weighted_quality=0.2,
            )
        ],
    )
    child = reflective_mutate(
        seed, signal, StubReflectionClient(), minibatch=signal.failing_cases, next_id="c1"
    )
    child_score = runner.run(child, dataset_split="benchmark_holdout").composite
    assert child_score > seed_score
    assert "appeal_vector_capture" in child.dimension_targets
