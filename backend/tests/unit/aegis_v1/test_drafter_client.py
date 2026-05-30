from app.aegis_v1.drafter_client import DrafterLLMClient, StubDrafterClient


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
