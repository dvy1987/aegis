from __future__ import annotations

from app.aegis_v1.pipeline import run_aegis_v1_pipeline
from app.aegis_v1.schemas import AppealPackage
from app.aegis_v1.drafter_client import StubDrafterClient


CIGNA_DENIAL = """Dear Member,
Cigna denied Intensive Outpatient Program for Obsessive-Compulsive Disorder
because medical necessity was not shown. Appeal within 180 days.
"""


def test_pipeline_stamps_search_planner_trace_metadata() -> None:
    package = AppealPackage.model_validate(
        run_aegis_v1_pipeline(
            denial_text=CIGNA_DENIAL,
            clinical_context="Severe OCD requiring IOP.",
            case_id="meta_case",
            drafter_client=StubDrafterClient(),
        )
    )
    meta = package.trace_metadata
    assert meta.search_planner_version == "search_planner_v1"
    assert meta.library_search_query
    assert "Cigna" in meta.library_search_query
    assert meta.discovery_enabled is False
