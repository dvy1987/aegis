from app.learning.models import Candidate, Component
from app.learning.merge import system_aware_merge


def _c(cid, prompt_v, pb_v):
    return Candidate(candidate_id=cid, components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", version=prompt_v, text=prompt_v),
        "playbook:Cigna:medical_necessity:not_evidence_based": Component(
            component_id="playbook:Cigna:medical_necessity:not_evidence_based", kind="playbook", version=pb_v,
            playbook={"v": pb_v})})


def test_merge_takes_each_lineages_improved_component():
    a = _c("a", "v2", "v1")   # a improved the prompt
    b = _c("b", "v1", "v2")   # b improved the playbook
    base = _c("seed", "v1", "v1")
    merged = system_aware_merge(a, b, base=base, next_id="m1")
    assert merged is not None
    assert merged.components["drafter_system_prompt"].version == "v2"      # from a
    assert merged.components["playbook:Cigna:medical_necessity:not_evidence_based"].version == "v2"  # from b
    assert merged.origin == "merge"


def test_merge_returns_none_on_conflict_same_component():
    a = _c("a", "v2", "v1")
    b = _c("b", "v3", "v1")   # both edited the prompt -> conflict
    base = _c("seed", "v1", "v1")
    assert system_aware_merge(a, b, base=base, next_id="m1") is None
