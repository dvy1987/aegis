from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.aegis_v1.schemas import CitationHit, ParsedCase, RetrievalResult
from app.aegis_swarm.corpus_store import DOMAIN_SUBDIR

if TYPE_CHECKING:
    from app.aegis_swarm.corpus_store import CorpusHit, CorpusStore

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")


def _tokenize(text: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD_RE.finditer(text or "")}


_DENIAL_SYNONYMS: dict[str, set[str]] = {
    "medical_necessity": {"medical", "necessity", "mednec", "clinical"},
    "prior_authorization": {"prior", "authorization", "auth"},
    "coverage_exclusion": {"coverage", "exclusion", "excluded"},
}


def search_unified_library(
    store: "CorpusStore", query: str, top_k: int = 3
) -> list["CorpusHit"]:
    """Search all corpus domains and return the top hits by relevance."""
    domains = store.list_domains() or list(DOMAIN_SUBDIR.keys())
    merged: list[CorpusHit] = []
    for domain in domains:
        merged.extend(store.search(domain, query, top_k=top_k))
    merged.sort(key=lambda h: h.relevance_score, reverse=True)
    return merged[:top_k]


def hit_to_citation(hit: "CorpusHit") -> CitationHit:
    return CitationHit(
        corpus_doc_id=hit.corpus_doc_id,
        title=hit.title,
        quote=hit.quote,
        relevance_score=hit.relevance_score,
    )


def hits_to_retrieval(query: str, hits: list["CorpusHit"]) -> dict:
    return RetrievalResult(
        query=query,
        hits=[hit_to_citation(h) for h in hits],
    ).model_dump()


def is_citable_for_case(parsed: ParsedCase, hit: CitationHit) -> bool:
    """FR-2 / CL-1: hit must plausibly support this insurer + denial slice."""
    blob = f"{hit.title} {hit.quote} {hit.corpus_doc_id}".lower()
    tokens = _tokenize(blob)

    insurer = (parsed.insurer or "").lower()
    if insurer and insurer != "unknown" and insurer not in blob:
        return False

    denial = parsed.denial_type
    if denial and denial != "unknown":
        denial_spaced = denial.replace("_", " ")
        synonyms = _DENIAL_SYNONYMS.get(denial, set())
        if denial_spaced not in blob and not (synonyms & tokens):
            return False

    return True


def library_is_thin(parsed: ParsedCase, hits: list[CitationHit]) -> bool:
    if not hits:
        return True
    return not any(is_citable_for_case(parsed, h) for h in hits)
