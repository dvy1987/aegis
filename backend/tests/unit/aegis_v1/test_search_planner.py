from __future__ import annotations

from app.aegis_v1.search_planner import (
    apply_query_guardrails,
    build_baseline_query,
    refine_discovery_query,
)
from app.aegis_v1.planner_refinement_client import StubPlannerRefinementClient


def test_build_baseline_query_from_case_fields() -> None:
    q = build_baseline_query(
        {
            "insurer": "Cigna",
            "denial_type": "medical_necessity",
            "service_or_procedure": "IOP",
            "diagnosis_summary": "OCD",
            "cited_denial_reason": "not medically necessary",
        }
    )
    assert "Cigna" in q
    assert "medical necessity" in q
    assert "OCD" in q


def test_broad_query_guardrail_rejects_and_falls_back() -> None:
    phrase, rejected = apply_query_guardrails(
        "search the entire web for insurance",
        fallback="Cigna medical necessity guideline",
    )
    assert rejected is True
    assert phrase == "Cigna medical necessity guideline"


def test_layer3_refine_differs_from_fetch_one() -> None:
    parsed = {
        "insurer": "Cigna",
        "denial_type": "medical_necessity",
        "service_or_procedure": "IOP",
        "diagnosis_summary": "OCD",
        "cited_denial_reason": "denied",
    }
    base = build_baseline_query(parsed)
    q2, ran = refine_discovery_query(
        parsed_case=parsed,
        fetch_index=1,
        prior_queries=[base],
        hit_count=0,
        ingest_count=0,
        reject_count=1,
        client=StubPlannerRefinementClient(),
    )
    assert ran is True
    assert q2 != base
