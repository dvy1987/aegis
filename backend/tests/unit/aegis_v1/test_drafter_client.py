from app.aegis_v1.drafter_client import (
    DrafterLLMClient,
    GeminiDrafterClient,
    StubDrafterClient,
    _build_contents,
    build_drafter_message,
    format_drafter_user_inputs,
)
from app.aegis_v1.tools import DISCLAIMER, draft_appeal


def test_patient_inputs_are_plain_text_without_json() -> None:
    text = format_drafter_user_inputs(
        denial_text="Aetna denied TMS.",
        clinical_context="PHQ-9 23",
    )
    assert "DENIAL LETTER:" in text
    assert "CLINICAL CONTEXT:" in text
    assert "{" not in text


def test_internal_pipeline_context_is_attached_separately() -> None:
    message = build_drafter_message(
        denial_text="Aetna denied TMS.",
        clinical_context="PHQ-9 23",
        citations=[{"corpus_doc_id": "erisa_503.md", "title": "ERISA", "quote": "review"}],
        playbook={"tactics": ["Rebut medical necessity."], "version": "day_zero"},
        phoenix_summary={"status": "cold_start", "success_traits": []},
    )
    assert "DENIAL LETTER:" in message
    assert "LIBRARY CITATIONS:" in message
    assert "PLAYBOOK:" in message
    assert "PHOENIX MEMORY:" in message
    assert "insurer" not in message


def test_drafter_llm_message_excludes_parsed_case_scaffolding() -> None:
    parsed = {
        "denial_text": "Aetna denied TMS.",
        "clinical_context": "PHQ-9 23",
        "insurer": "Aetna",
        "diagnosis_summary": "should not appear",
    }
    message = _build_contents(
        "SYSTEM",
        parsed,
        [{"corpus_doc_id": "erisa_503.md", "title": "ERISA", "quote": "review"}],
        {"tactics": ["Rebut."], "version": "day_zero"},
        {"status": "cold_start", "query": "q"},
    )
    assert "diagnosis_summary" not in message
    assert "LIBRARY CITATIONS:" in message
    assert "PLAYBOOK:" in message
    assert "PHOENIX MEMORY:" in message


def test_stub_client_is_a_drafter_llm_client():
    client: DrafterLLMClient = StubDrafterClient()
    assert client.name == "stub_drafter"


def test_stub_client_returns_deterministic_letter_body_from_inputs():
    client = StubDrafterClient()
    body = client.draft(
        prompt="ignored in stub",
        parsed_case={"insurer": "Cigna", "service_or_procedure": "TMS",
                     "cited_denial_reason": "not medically necessary",
                     "clinical_context": "failed two SSRIs"},
        citations=[{"corpus_doc_id": "erisa_503.md", "title": "ERISA", "quote": "full and fair review"}],
        playbook={"tactics": ["Rebut the medical-necessity rationale."]},
        phoenix_summary={"success_traits": ["cite local corpus"]},
    )
    assert "Cigna" in body
    assert "TMS" in body
    # deterministic: same inputs -> same output
    again = client.draft("ignored", {"insurer": "Cigna", "service_or_procedure": "TMS",
                                     "cited_denial_reason": "not medically necessary",
                                     "clinical_context": "failed two SSRIs"},
                         [{"corpus_doc_id": "erisa_503.md", "title": "ERISA", "quote": "full and fair review"}],
                         {"tactics": ["Rebut the medical-necessity rationale."]},
                         {"success_traits": ["cite local corpus"]})
    assert body == again


def test_drafter_uses_injected_client_and_applies_guardrails():
    parsed = {"case_id": "case_demo", "insurer": "Cigna", "denial_type": "medical_necessity",
              "service_or_procedure": "TMS",
              "diagnosis_summary": "treatment-resistant depression",
              "cited_denial_reason": "not medically necessary",
              "denial_text": "We denied coverage for TMS as not medically necessary.",
              "clinical_context": "failed two SSRIs", "missing_facts": ["plan_document_language"]}
    retrieval = {"query": "x", "hits": [
        {"corpus_doc_id": "erisa_503.md", "title": "ERISA 503", "quote": "full and fair review", "relevance_score": 1.0}]}
    playbook = {"insurer": "Cigna", "denial_type": "medical_necessity", "version": "cold-start",
                "status": "missing", "tactics": ["Rebut the rationale."], "required_evidence": ["clinical notes"],
                "risk_flags": ["playbook_cold_start"]}
    phoenix = {"status": "cold_start", "query": "q", "similar_trace_count": 0,
               "failure_patterns": [], "success_traits": [], "risk_flags": ["phoenix_mcp_cold_start"]}

    out = draft_appeal(parsed, retrieval, playbook, phoenix, client=StubDrafterClient())

    assert DISCLAIMER.lower() in out["appeal_letter"].lower()   # guardrail injected
    assert out["citations_used"][0]["corpus_doc_id"] == "erisa_503.md"  # only retrieved cites attached
    # Prompt version is part of risk flags: either v1-weak or a promoted prompt tag.
    assert (
        "weak_prompt_v1" in out["risk_flags"]
        or any(str(f).startswith("prompt:") for f in out["risk_flags"])
    )
    assert out["safety_disclaimer"] == DISCLAIMER


def test_gemini_drafter_client_constructs_with_default_model(monkeypatch):
    monkeypatch.delenv("AEGIS_DRAFTER_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    client = GeminiDrafterClient()
    assert client.name == "gemini"
    assert client.model in {"gemini-3.1-pro-preview", "gemini-2.5-pro"}
    assert client.location == "global"
