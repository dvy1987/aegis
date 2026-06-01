from __future__ import annotations

from app.aegis_swarm.literature_discovery import FakeDiscoverySearchClient
from app.aegis_swarm.vertex_discovery import (
    VertexGroundedDiscoveryClient,
    _parse_candidates,
    build_discovery_search_client,
    vertex_discovery_enabled,
)


def test_vertex_discovery_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AEGIS_VERTEX_DISCOVERY", raising=False)
    assert vertex_discovery_enabled() is False
    assert isinstance(build_discovery_search_client(), FakeDiscoverySearchClient)


def test_build_discovery_client_returns_vertex_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_VERTEX_DISCOVERY", "true")
    client = build_discovery_search_client()
    assert isinstance(client, VertexGroundedDiscoveryClient)


def test_parse_candidates_extracts_urls() -> None:
    text = (
        "- NIH standards https://www.ncbi.nlm.nih.gov/pmc/articles/PMCFAKE1 "
        "Peer-reviewed synthesis.\n"
        "- Blog https://random-blog.example.com/tips Unvetted content."
    )
    cands = _parse_candidates(text, "clinical")
    assert len(cands) == 2
    assert "nih.gov" in cands[0].source_url
    assert cands[0].domain == "clinical"
