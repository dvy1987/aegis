from __future__ import annotations

from pathlib import Path

import pytest

from app.aegis_v1.library_context import prepare_library_context
from app.aegis_v1.tools import case_parser
from app.aegis_swarm.corpus_store import LocalCorpusStore
from app.aegis_swarm.literature_discovery import (
    DiscoveryConfig,
    DiscoveryCandidate,
    FakeDiscoverySearchClient,
    LiteratureDiscovery,
)

CIGNA_DENIAL = """Dear Member,
Cigna denied Intensive Outpatient Program for Obsessive-Compulsive Disorder
because medical necessity was not shown. Appeal within 180 days.
"""


@pytest.fixture
def empty_corpus(tmp_path: Path) -> Path:
    for sub in ("clinical", "legal", "precedent", "insurer"):
        (tmp_path / sub).mkdir(parents=True)
    return tmp_path


def test_discovery_off_flags_thin_library(empty_corpus: Path) -> None:
    parsed = case_parser(denial_text=CIGNA_DENIAL, case_id="thin_off")
    discovery = LiteratureDiscovery(
        corpus_dir=empty_corpus,
        config=DiscoveryConfig(enabled=False),
    )
    ctx = prepare_library_context(
        parsed,
        case_id="thin_off",
        corpus_store=LocalCorpusStore(empty_corpus),
        discovery=discovery,
    )
    assert "library_thin_no_discovery" in ctx.risk_flags
    assert ctx.metadata.discovery_fetch_count == 0


def test_discovery_on_ingests_and_researches(tmp_path: Path) -> None:
    empty = tmp_path / "corpus"
    for sub in ("clinical", "legal", "precedent", "insurer"):
        (empty / sub).mkdir(parents=True)

    fake = FakeDiscoverySearchClient(
        candidates=[
            DiscoveryCandidate(
                title="Cigna OCD medical necessity evidence",
                source_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123",
                snippet=(
                    "Cigna medical necessity peer-reviewed evidence for OCD "
                    "intensive outpatient treatment."
                ),
                domain="clinical",
            )
        ]
    )
    discovery = LiteratureDiscovery(
        corpus_dir=empty,
        search_client=fake,
        config=DiscoveryConfig(enabled=True, per_case_cap=5, per_day_cap=20),
    )
    parsed = case_parser(
        denial_text=CIGNA_DENIAL,
        clinical_context="Severe OCD requiring IOP.",
        case_id="thin_on",
    )
    ctx = prepare_library_context(
        parsed,
        case_id="thin_on",
        corpus_store=LocalCorpusStore(empty),
        discovery=discovery,
        refinement_client=None,
    )
    assert ctx.metadata.discovery_ran is True
    assert ctx.metadata.discovery_fetch_count >= 1
    assert ctx.metadata.discovery_ingested_count >= 1
    assert len(ctx.retrieval["hits"]) >= 1


def test_controlled_retrieval_ignores_model_query() -> None:
    from app.aegis_v1.retrieval_context import reset_controlled_retrieval, set_controlled_retrieval
    from app.aegis_v1.tools import corpus_retrieval

    controlled = {
        "query": "planner-query",
        "hits": [
            {
                "corpus_doc_id": "x.md",
                "title": "X",
                "quote": "quote",
                "relevance_score": 1.0,
            }
        ],
    }
    token = set_controlled_retrieval(controlled)
    try:
        out = corpus_retrieval(query="model-should-not-win", top_k=3)
    finally:
        reset_controlled_retrieval(token)
    assert out["query"] == "planner-query"
    assert out["hits"][0]["corpus_doc_id"] == "x.md"
