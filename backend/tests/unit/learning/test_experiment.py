from app.learning.models import Candidate, Component
from app.learning.experiment import StubExperimentRunner


DATASET = [
    {"case_id": "a", "slice": "Cigna:medical_necessity:not_evidence_based", "base": {"appeal_vector_capture": 1, "grounding": 3}},
    {"case_id": "b", "slice": "Cigna:medical_necessity:not_evidence_based", "base": {"appeal_vector_capture": 1, "grounding": 3}},
]


def _seed():
    return Candidate(candidate_id="seed", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", text="draft"),
        "playbook:Cigna:medical_necessity:not_evidence_based": Component(
            component_id="playbook:Cigna:medical_necessity:not_evidence_based", kind="playbook",
            playbook={"tactics": [], "dimension_targets": []})})


def _improved():
    c = _seed()
    c.components["playbook:Cigna:medical_necessity:not_evidence_based"].playbook["dimension_targets"] = ["appeal_vector_capture"]
    return c.model_copy(update={"candidate_id": "improved"})


def test_stub_runner_scores_per_case_and_mean():
    res = StubExperimentRunner(DATASET).run(_seed(), dataset_split="benchmark_holdout")
    assert len(res.per_case) == 2
    assert res.composite == res.per_case[0].composite   # identical cases


def test_targeting_the_weak_dimension_raises_the_composite():
    seed_score = StubExperimentRunner(DATASET).run(_seed(), dataset_split="benchmark_holdout").composite
    improved_score = StubExperimentRunner(DATASET).run(_improved(), dataset_split="benchmark_holdout").composite
    assert improved_score > seed_score   # the loop has real signal to climb
