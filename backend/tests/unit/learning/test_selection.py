from app.learning.models import Candidate, Component
from app.learning.selection import pareto_frontier, pareto_select, select_component


def _cand(cid):
    return Candidate(candidate_id=cid, components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="x")})


def test_pareto_frontier_drops_strictly_dominated():
    pool = [_cand("a"), _cand("b"), _cand("c")]
    scores = {"a": {"1": 0.8, "2": 0.2}, "b": {"1": 0.2, "2": 0.8}, "c": {"1": 0.1, "2": 0.1}}
    front = {c.candidate_id for c in pareto_frontier(pool, scores)}
    assert front == {"a", "b"}            # c is dominated on every case


def test_pareto_select_prefers_widest_coverage():
    pool = [_cand("a"), _cand("b")]
    scores = {"a": {"1": 0.9, "2": 0.9}, "b": {"1": 0.9, "2": 0.1}}
    assert pareto_select(pool, scores).candidate_id == "a"   # a wins both cases


def test_select_component_round_robins_for_coverage():
    parent = Candidate(candidate_id="p", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="x"),
        "playbook:Cigna:medical_necessity:not_evidence_based": Component(
            component_id="playbook:Cigna:medical_necessity:not_evidence_based", kind="playbook",
            playbook={"tactics": [], "dimension_targets": []})})
    picks = [select_component(parent, i) for i in range(4)]
    assert picks == ["drafter_system_prompt", "playbook:Cigna:medical_necessity:not_evidence_based",
                     "drafter_system_prompt", "playbook:Cigna:medical_necessity:not_evidence_based"]
