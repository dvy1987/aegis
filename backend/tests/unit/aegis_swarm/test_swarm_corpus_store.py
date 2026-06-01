from __future__ import annotations

from pathlib import Path

from app.aegis_swarm.corpus_store import (
    CorpusStore,
    LocalCorpusStore,
    classify_trust_tier,
)


def test_local_store_lists_domain_subdirs() -> None:
    domains = LocalCorpusStore().list_domains()
    for expected in ("clinical", "legal", "precedent", "insurer"):
        assert expected in domains


def test_local_store_satisfies_protocol() -> None:
    assert isinstance(LocalCorpusStore(), CorpusStore)


def test_legal_search_returns_traceable_hits() -> None:
    hits = LocalCorpusStore().search(
        "legal", "ERISA full and fair review 180 days appeal", top_k=2
    )
    assert hits
    assert all(h.corpus_doc_id.endswith(".md") for h in hits)
    assert all(h.quote for h in hits)
    assert all(h.domain == "legal" for h in hits)


def test_clinical_search_finds_clinical_seed_doc() -> None:
    hits = LocalCorpusStore().search("clinical", "medical necessity evidence MCG InterQual")
    assert any(h.corpus_doc_id == "medical_necessity_evidence.md" for h in hits)


def test_policy_domain_maps_to_insurer_subdir() -> None:
    hits = LocalCorpusStore().search("policy", "Cigna medical necessity appeal criteria")
    assert hits
    assert any("cigna" in h.corpus_doc_id for h in hits)


def test_hit_converts_to_brief_citation() -> None:
    hit = LocalCorpusStore().search("legal", "ERISA appeal", top_k=1)[0]
    citation = hit.to_brief_citation()
    assert citation.corpus_doc_id == hit.corpus_doc_id
    assert citation.quote == hit.quote


def test_empty_corpus_dir_returns_no_hits(tmp_path: Path) -> None:
    store = LocalCorpusStore(corpus_dir=tmp_path)
    assert store.search("legal", "anything") == []
    assert store.list_domains() == []


def test_trust_tier_allow_list() -> None:
    assert classify_trust_tier("https://www.ecfr.gov/current/title-29") == "gov_regulatory"
    assert classify_trust_tier("https://pubmed.ncbi.nlm.nih.gov/12345") == "peer_reviewed"
    assert classify_trust_tier("https://www.propublica.org/article") == "journalism"
    assert classify_trust_tier("https://tdi.texas.gov/iro/decision") == "state_doi_iro"
    assert classify_trust_tier("https://random-blog.example.com/post") is None
    assert classify_trust_tier("") is None
