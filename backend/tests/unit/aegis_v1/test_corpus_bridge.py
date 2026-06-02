from __future__ import annotations

from app.aegis_v1.corpus_bridge import is_citable_for_case, library_is_thin
from app.aegis_v1.schemas import CitationHit, ParsedCase


def _case() -> ParsedCase:
    return ParsedCase(
        case_id="c1",
        insurer="Cigna",
        denial_type="medical_necessity",
        service_or_procedure="IOP",
        diagnosis_summary="OCD",
        cited_denial_reason="not necessary",
        denial_text="denied",
    )


def test_mismatched_insurer_hit_is_not_citable() -> None:
    hit = CitationHit(
        corpus_doc_id="aetna_only.md",
        title="Aetna policy",
        quote="Aetna medical necessity policy for members",
    )
    assert is_citable_for_case(_case(), hit) is False
    assert library_is_thin(_case(), [hit]) is True


def test_matching_insurer_and_denial_is_citable() -> None:
    hit = CitationHit(
        corpus_doc_id="cigna_medical_necessity.md",
        title="Cigna Medical Necessity",
        quote="Cigna medical necessity criteria for the requested service",
    )
    assert is_citable_for_case(_case(), hit) is True
    assert library_is_thin(_case(), [hit]) is False
