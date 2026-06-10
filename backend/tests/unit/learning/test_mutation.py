from app.learning.models import Candidate, Component, DimensionSignal
from app.learning.mutation import reflective_mutate
from app.learning.reflection_client import StubReflectionClient


def _parent():
    return Candidate(candidate_id="p", components={
        "drafter_system_prompt": Component(component_id="drafter_system_prompt", kind="prompt", version="v1", text="x"),
        "playbook:Cigna:medical_necessity:not_evidence_based": Component(
            component_id="playbook:Cigna:medical_necessity:not_evidence_based", kind="playbook", version="v1",
            playbook={"tactics": [], "dimension_targets": []})})


def test_mutation_edits_exactly_one_component_and_records_lineage():
    sig = DimensionSignal(component_id="playbook:Cigna:medical_necessity:not_evidence_based",
                          weakest_dimension="appeal_vector_capture", failing_cases=[], notes={})
    child = reflective_mutate(_parent(), sig, StubReflectionClient(), minibatch=[], next_id="c1")
    assert child.parent_id == "p"
    assert child.origin == "reflect"
    assert child.dimension_targets == ["appeal_vector_capture"]
    # exactly one component changed (the targeted playbook); the prompt is untouched
    assert child.components["drafter_system_prompt"] == _parent().components["drafter_system_prompt"]
    assert child.components["playbook:Cigna:medical_necessity:not_evidence_based"].version == "v2"
    assert "appeal_vector_capture" in child.components["playbook:Cigna:medical_necessity:not_evidence_based"].playbook["dimension_targets"]
