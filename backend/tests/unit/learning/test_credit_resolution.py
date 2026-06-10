from app.learning.credit_resolution import (
    EVOLVABLE_AGENT_ROLES,
    resolve_credit_target,
)
from app.learning.models import ScoredRun


def _run(case_id: str, dims: dict, signals: list | None = None) -> ScoredRun:
    full = {
        "grounding": 5,
        "appeal_vector_capture": 5,
        "case_specific_clinical_rebuttal": 5,
        "question_agent": 5,
        "persuasive_coherence": 5,
    }
    full.update(dims)
    return ScoredRun(
        case_id=case_id,
        slice="Cigna:medical_necessity:not_evidence_based",
        dimension_scores=full,
        hard_gate_pass=True,
        weighted_quality=0.4,
        swarm_trace_signals=signals or [],
    )


def test_weakest_dimension_routes_to_strategist():
    runs = [
        _run("a", {"appeal_vector_capture": 1, "grounding": 5}),
        _run("b", {"appeal_vector_capture": 1, "grounding": 5}),
    ]
    res = resolve_credit_target(runs)
    assert res.action == "evolve_prompt"
    assert res.component_id == "strategist"


def test_clinical_dimension_routes_to_medical_necessity():
    runs = [_run("a", {"case_specific_clinical_rebuttal": 1, "grounding": 5})]
    res = resolve_credit_target(runs)
    assert res.component_id == "medical_necessity"


def test_researcher_override_on_empty_retrieval():
    signals = [
        {
            "role": "policy_detective",
            "status": "empty",
            "risk_flags": ["cpb_not_found"],
        }
    ]
    runs = [
        _run(
            "a",
            {"grounding": 1},
            signals=signals,
        )
    ]
    res = resolve_credit_target(runs)
    assert res.action == "evolve_prompt"
    assert res.component_id == "policy_detective"
    assert res.researcher_override is True


def test_corpus_gap_when_multiple_researchers_empty_for_grounding():
    signals = [
        {"role": "medical_necessity", "status": "empty", "risk_flags": ["no_guidelines_found"]},
        {"role": "policy_detective", "status": "partial", "risk_flags": ["cpb_not_found"]},
    ]
    runs = [_run("a", {"grounding": 1}, signals=signals)]
    res = resolve_credit_target(runs)
    assert res.action == "corpus_gap"


def test_all_pipeline_agents_except_orchestrator_are_evolvable():
    assert "orchestrator" not in EVOLVABLE_AGENT_ROLES
    assert "drafter" in EVOLVABLE_AGENT_ROLES
    assert "triage" in EVOLVABLE_AGENT_ROLES
    assert "legal_researcher" in EVOLVABLE_AGENT_ROLES
    assert "adversarial_reviewer" in EVOLVABLE_AGENT_ROLES
