from __future__ import annotations

from pathlib import Path

from app.aegis_swarm.corpus_store import CorpusHit, LocalCorpusStore
from app.aegis_swarm.vertex_search import (
    LocalDelegatingVertexBackend,
    VertexSearchCorpusStore,
    build_corpus_store,
    vertex_search_configured,
)


def test_vertex_search_not_configured_by_default(monkeypatch) -> None:
    monkeypatch.delenv("VERTEX_SEARCH_DATA_STORE_ID", raising=False)
    assert vertex_search_configured() is False
    assert isinstance(build_corpus_store(), LocalCorpusStore)


def test_build_corpus_store_uses_vertex_wrapper_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE_ID", "test-store")
    monkeypatch.setenv("VERTEX_SEARCH_PROJECT", "test-project")
    store = build_corpus_store()
    assert isinstance(store, VertexSearchCorpusStore)


def test_vertex_store_falls_back_to_local_when_not_configured(tmp_path: Path) -> None:
    legal = tmp_path / "legal"
    legal.mkdir()
    (legal / "erisa.md").write_text("# ERISA\n\nFull and fair review within 180 days.\n")
    backend = LocalDelegatingVertexBackend(tmp_path)
    store = VertexSearchCorpusStore(backend, fallback=LocalCorpusStore(tmp_path))
    hits = store.search("legal", "ERISA appeal 180 days", top_k=1)
    assert hits
    assert hits[0].corpus_doc_id == "erisa.md"


def test_vertex_store_uses_backend_when_configured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE_ID", "ds-1")

    class FixedBackend:
        def search(self, domain, query, top_k):
            return [
                CorpusHit(
                    corpus_doc_id="vertex-only.md",
                    title="Vertex",
                    quote="From vertex",
                    relevance_score=1.0,
                    domain=domain,
                )
            ]

    store = VertexSearchCorpusStore(FixedBackend(), fallback=LocalCorpusStore(tmp_path))
    hits = store.search("legal", "anything", top_k=1)
    assert hits[0].corpus_doc_id == "vertex-only.md"
