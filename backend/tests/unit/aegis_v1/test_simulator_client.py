from app.aegis_v1.schemas import FeatureAssessment
from app.aegis_v1.simulator_client import (
    GeminiSimulatorClient,
    SimulatorClient,
    StubSimulatorClient,
    uniform_assessment,
)
from app.aegis_v1.tools import simulator


def _parsed():
    return {"case_id": "c1", "insurer": "Cigna", "denial_type": "medical_necessity",
            "service_or_procedure": "TMS", "diagnosis_summary": "treatment-resistant depression",
            "cited_denial_reason": "not medically necessary",
            "denial_text": "Denied: not medically necessary.",
            "clinical_context": "failed two SSRIs"}


def _draft():
    return {"case_summary": "Cigna denied TMS.", "denial_grounds_interpreted": "not medically necessary",
            "appeal_strategy": "Rebut the rationale.",
            "appeal_letter": "Please conduct a full and fair review of the denial.",
            "citations_used": [], "missing_evidence_checklist": [], "risk_flags": [],
            "safety_disclaimer": "Not legal or medical advice. Draft assistance only."}


def test_stub_simulator_is_a_simulator_client():
    client: SimulatorClient = StubSimulatorClient()
    assert client.name == "stub_simulator"


def test_gemini_simulator_constructs_with_default_model(monkeypatch):
    monkeypatch.delenv("AEGIS_SIMULATOR_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    client = GeminiSimulatorClient()
    assert client.name == "gemini_simulator"
    assert client.model in {"gemini-3.1-pro-preview", "gemini-2.5-pro"}
    assert client.location == "global"


def test_simulator_tool_denies_on_weak_assessment():
    out = simulator(parsed_case=_parsed(), appeal_draft=_draft(),
                    self_check_result={}, client=StubSimulatorClient(assessment=uniform_assessment(1)))
    assert out["verdict"] == "DENY"
    assert out["score"] == 0.2
    assert out["gaps"]


def test_simulator_tool_approves_on_strong_assessment():
    out = simulator(parsed_case=_parsed(), appeal_draft=_draft(),
                    self_check_result={}, client=StubSimulatorClient(assessment=uniform_assessment(5)))
    assert out["verdict"] == "APPROVE"
    assert out["score"] == 1.0
    assert out["gaps"] == []


def test_uniform_assessment_marks_all_rubric_features():
    fa = uniform_assessment(5)
    assert isinstance(fa, FeatureAssessment)
    assert fa.features["rebuts_specific_flaw"].anchor == 5
    assert len(fa.features) == 6


def test_stub_assess_returns_the_configured_assessment():
    fa = uniform_assessment(3)
    out = StubSimulatorClient(assessment=fa).assess(
        denial_text="d", clinical_context="c", appeal_letter="a")
    assert out.features["credible_tone"].anchor == 3


def test_stub_assess_defaults_to_weak():
    out = StubSimulatorClient().assess(denial_text="d", clinical_context="c", appeal_letter="a")
    assert out.features["rebuts_specific_flaw"].anchor == 1
