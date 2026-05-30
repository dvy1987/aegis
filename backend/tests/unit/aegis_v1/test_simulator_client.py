from app.aegis_v1.simulator_client import (
    GeminiSimulatorClient,
    SimulatorClient,
    StubSimulatorClient,
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
    client: SimulatorClient = StubSimulatorClient(verdict="APPROVE", score=10)
    assert client.name == "stub_simulator"


def test_stub_simulator_returns_requested_outcome():
    out = StubSimulatorClient(verdict="APPROVE", score=10).simulate(_parsed(), _draft())
    assert out["verdict"] == "APPROVE"
    assert out["score"] == 10
    assert out["threshold"] == 10
    assert isinstance(out["features"], dict)


def test_gemini_simulator_constructs_with_default_model(monkeypatch):
    monkeypatch.delenv("AEGIS_SIMULATOR_MODEL", raising=False)
    client = GeminiSimulatorClient()
    assert client.name == "gemini_simulator"
    assert client.model == "gemini-3.1-pro"
    assert client.location == "global"
    assert client.threshold == 10  # weak-v1 demo arc: perfect 10 required to APPROVE


def test_simulator_tool_uses_injected_client():
    out = simulator(parsed_case=_parsed(), appeal_draft=_draft(),
                    self_check_result={}, client=StubSimulatorClient(verdict="DENY", score=2))
    assert out["verdict"] == "DENY"
    assert out["score"] == 2
