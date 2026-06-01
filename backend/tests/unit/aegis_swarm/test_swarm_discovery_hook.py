from __future__ import annotations

from pathlib import Path

from app.aegis_swarm.literature_discovery import (
    DiscoveryCandidate,
    DiscoveryConfig,
    FakeDiscoverySearchClient,
    LiteratureDiscovery,
)
from app.aegis_swarm.tools import corpus_search_with_discovery


def test_thin_retrieval_triggers_discovery_ingest(tmp_path: Path) -> None:
    clinical = tmp_path / "clinical"
    clinical.mkdir()
    fake = FakeDiscoverySearchClient(
        [
            DiscoveryCandidate(
                title="NIH evidence standards",
                source_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMCFAKE2",
                snippet="Clean peer-reviewed snippet for ingest.",
                domain="clinical",
            )
        ]
    )
    discovery = LiteratureDiscovery(
        corpus_dir=tmp_path,
        search_client=fake,
        config=DiscoveryConfig(enabled=True, per_case_cap=3, per_day_cap=10),
    )
    from app.aegis_swarm.corpus_store import LocalCorpusStore

    store = LocalCorpusStore(tmp_path)
    hits, meta = corpus_search_with_discovery(
        store,
        "clinical",
        "medical necessity MCG",
        top_k=3,
        case_id="case-thin",
        discovery=discovery,
    )
    assert meta is not None
    assert meta["ingested"]
    assert any(h.corpus_doc_id.startswith("disc-") for h in hits)


def test_full_retrieval_skips_discovery(tmp_path: Path) -> None:
    clinical = tmp_path / "clinical"
    clinical.mkdir()
    (clinical / "seed.md").write_text(
        "# Seed\n\nMedical necessity evidence MCG InterQual guidelines.\n"
    )
    from app.aegis_swarm.corpus_store import LocalCorpusStore

    store = LocalCorpusStore(tmp_path)
    discovery = LiteratureDiscovery(
        corpus_dir=tmp_path,
        config=DiscoveryConfig(enabled=True),
    )
    hits, meta = corpus_search_with_discovery(
        store,
        "clinical",
        "medical necessity MCG InterQual",
        top_k=1,
        case_id="case-full",
        discovery=discovery,
    )
    assert len(hits) >= 1
    assert meta is None
