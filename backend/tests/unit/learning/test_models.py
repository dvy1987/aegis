from app.learning.models import (
    Candidate, CaseScore, Component, DIMENSIONS, DIMENSION_WEIGHTS,
    ExperimentResult, composite_score,
)


def test_dimension_weights_sum_to_one():
    assert set(DIMENSION_WEIGHTS) == set(DIMENSIONS)
    assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


def test_composite_all_fives_is_one_all_ones_is_point_two():
    assert composite_score({d: 5 for d in DIMENSIONS}, hard_gate_pass=True) == 1.0
    assert composite_score({d: 1 for d in DIMENSIONS}, hard_gate_pass=True) == 0.2


def test_composite_hard_gate_fail_is_zero():
    assert composite_score({d: 5 for d in DIMENSIONS}, hard_gate_pass=False) == 0.0


def test_missing_dimension_defaults_to_anchor_one():
    assert composite_score({"grounding": 5}, hard_gate_pass=True) == round(
        0.10 * 1.0 + (0.40 + 0.25 + 0.15 + 0.10) * 0.2, 4)


def test_experiment_result_mean_and_dimension_means():
    r = ExperimentResult(
        candidate_id="c1", dataset_split="holdout",
        per_case=[
            CaseScore(case_id="a", composite=0.4, dimension_scores={d: 1 for d in DIMENSIONS}, hard_gate_pass=True),
            CaseScore(case_id="b", composite=0.8, dimension_scores={d: 5 for d in DIMENSIONS}, hard_gate_pass=True),
        ],
        composite=0.6,
    )
    assert r.composite == 0.6
    assert r.dimension_means()["grounding"] == 3.0


def test_candidate_carries_components_and_lineage():
    c = Candidate(candidate_id="x", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="draft well")},
        origin="seed")
    assert c.components["drafter_system_prompt"].kind == "prompt"
    assert c.parent_id is None
