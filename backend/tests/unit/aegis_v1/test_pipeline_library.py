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


class _ExplodingCorpusStore:
    """A corpus store that fails on every call — simulates the library being
    offline / Vertex throwing / a misconfigured backend."""

    def list_domains(self) -> list[str]:
        raise RuntimeError("library offline")

    def search(self, domain, query, top_k: int = 3):
        raise RuntimeError("library offline")


def test_pipeline_survives_library_failure() -> None:
    """A failing library must NOT break drafting or the optimization loop.

    The pipeline should still produce a valid AppealPackage with no citations
    and a degraded risk flag instead of raising.
    """
    library_stack = {
        "corpus_store": _ExplodingCorpusStore(),
        "discovery": None,
        "refinement_client": None,
        "uses_vertex_store": True,
    }
    package = AppealPackage.model_validate(
        run_aegis_v1_pipeline(
            denial_text=CIGNA_DENIAL,
            clinical_context="Severe OCD requiring IOP.",
            case_id="lib_fail_case",
            drafter_client=StubDrafterClient(),
            library_stack=library_stack,
        )
    )
    assert package.appeal_package_draft.appeal_letter
    assert package.appeal_package_draft.citations_used == []
    assert "library_search_error" in package.risk_flags
