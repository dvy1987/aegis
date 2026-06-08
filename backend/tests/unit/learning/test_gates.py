from app.learning.models import Candidate, CaseScore, Component, ExperimentResult
from app.learning.gates import evaluate_vetoes


def _exp(cid, comp, cases):
    return ExperimentResult(candidate_id=cid, dataset_split="benchmark_holdout", per_case=cases, composite=comp)


def _cand(diff_tokens=10):
    return Candidate(candidate_id="c", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="w " * diff_tokens)},
        diff_summary="d")


def test_no_vetoes_on_clean_improvement():
    before = _exp("seed", 0.5, [CaseScore(case_id="a", composite=0.5, dimension_scores={"grounding": 3}, hard_gate_pass=True)])
    after = _exp("c", 0.7, [CaseScore(case_id="a", composite=0.7, dimension_scores={"grounding": 5}, hard_gate_pass=True)])
    assert evaluate_vetoes(before, after, _cand()) == []


def test_veto_on_held_out_regression():
    before = _exp("seed", 0.7, [])
    after = _exp("c", 0.5, [])
    assert "held_out_regression" in evaluate_vetoes(before, after, _cand())


def test_veto_on_hard_gate_regression():
    before = _exp("seed", 0.5, [CaseScore(case_id="a", composite=0.5, dimension_scores={}, hard_gate_pass=True)])
    after = _exp("c", 0.6, [CaseScore(case_id="a", composite=0.0, dimension_scores={}, hard_gate_pass=False)])
    assert "safety_or_hard_gate_regression" in evaluate_vetoes(before, after, _cand())


def test_veto_on_oversized_diff():
    before = _exp("seed", 0.5, [])
    after = _exp("c", 0.9, [])
    assert "diff_too_large" in evaluate_vetoes(before, after, _cand(diff_tokens=500))
