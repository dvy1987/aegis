from __future__ import annotations

from app.aegis_v1.schemas import ParsedCase, RetrievalResult


def test_parsed_case_coerces_string_list_fields() -> None:
    case = ParsedCase.model_validate(
        {
            "case_id": "c1",
            "insurer": "Cigna",
            "denial_type": "medical_necessity",
            "service_or_procedure": "IOP",
            "diagnosis_summary": "OCD",
            "cited_denial_reason": "not medically necessary",
            "deadlines_mentioned": "180 days",
            "missing_facts": "plan_document_language",
            "denial_text": "denied",
        }
    )
    assert case.deadlines_mentioned == ["180 days"]
    assert case.missing_facts == ["plan_document_language"]


def test_retrieval_result_coerces_comma_separated_hit_ids() -> None:
    result = RetrievalResult.model_validate(
        {
            "query": "cigna medical necessity",
            "hits": "cigna_medical_necessity.md, mhpaea_parity.md",
        }
    )
    assert len(result.hits) == 2
    assert result.hits[0].corpus_doc_id == "cigna_medical_necessity.md"
