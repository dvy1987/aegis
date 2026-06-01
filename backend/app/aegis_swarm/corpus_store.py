"""CorpusStore seam for swarm researchers (ADR-007).

Retrieval goes through a ``CorpusStore`` Protocol with two backends:

- ``LocalCorpusStore`` - BM25 over ``backend/corpus/<subdir>/**.md``. Offline
  default, no credentials. Built here.
- ``VertexSearchCorpusStore`` - Vertex AI Search over a GCS-hosted corpus.
  Live, credential-gated (``vertex_search.py``).

Also defines the **trust-tier** vocabulary + allow-list classifier used by the
``LiteratureDiscovery`` pipeline (Phase 2): discovered literature must classify
to an allowed tier before it can be sanitized, provenance-stamped, and ingested.
Discovery feeds the corpus; the corpus stays the sole citation source.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi

from app.aegis_swarm.schemas import BriefCitation, ResearcherDomain

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = BACKEND_ROOT / "corpus"

# Researcher domain -> corpus subdirectory. Plan/policy documents are
# insurer-published, so the Policy Detective reads the insurer subtree.
DOMAIN_SUBDIR: dict[str, str] = {
    "clinical": "clinical",
    "legal": "legal",
    "precedent": "precedent",
    "insurer": "insurer",
    "policy": "insurer",
}


# --- Trust tiers + allow-list (for discovery, Phase 2) ----------------------

TrustTier = str  # one of TRUST_TIERS

TRUST_TIERS: tuple[str, ...] = (
    "gov_regulatory",  # .gov, eCFR, CMS
    "state_doi_iro",  # state Dept. of Insurance / IRO decisions
    "peer_reviewed",  # PubMed / NIH / journals
    "specialty_society",  # AMA, APA, ACOG, etc.
    "journalism",  # ProPublica
)

# Ordered (host-substring, tier) allow-list. MOST SPECIFIC FIRST - the generic
# ".gov" catch-all is matched last so e.g. nih.gov classifies as peer_reviewed,
# not gov_regulatory. Anything that matches nothing is REJECTED at the filter.
_ALLOWLIST: tuple[tuple[str, str], ...] = (
    ("ncbi.nlm.nih.gov", "peer_reviewed"),
    ("pubmed.ncbi.nlm.nih.gov", "peer_reviewed"),
    ("nih.gov", "peer_reviewed"),
    ("ama-assn.org", "specialty_society"),
    ("psychiatry.org", "specialty_society"),
    ("acog.org", "specialty_society"),
    ("propublica.org", "journalism"),
    ("ecfr.gov", "gov_regulatory"),
    ("cms.gov", "gov_regulatory"),
    ("medicaid.gov", "gov_regulatory"),
    (".gov", "gov_regulatory"),
)


def classify_trust_tier(source_url: str) -> str | None:
    """Return the trust tier for an allow-listed source, else ``None`` (reject).

    State DOI/IRO hosts vary, so a ``doi``/``iro``/``insurance`` hint on a
    ``.gov`` host is tagged ``state_doi_iro`` (checked before the generic
    ``.gov`` catch-all).
    """
    url = (source_url or "").lower()
    if not url:
        return None
    if (".gov" in url) and ("iro" in url or "doi" in url or "insurance" in url):
        return "state_doi_iro"
    for needle, tier in _ALLOWLIST:
        if needle in url:
            return tier
    return None


# --- Provenance --------------------------------------------------------------


class CorpusProvenance(BaseModel):
    """Where a corpus document came from. Required for every ingested doc so
    citations remain auditable (no invented authorities)."""

    doc_id: str
    domain: ResearcherDomain
    title: str = ""
    source_url: str = ""
    source_tier: str = "seed"  # a TrustTier, or "seed" for hand-curated docs
    retrieved_at: str = ""  # ISO date; empty for seed docs
    ingest_mode: str = "seed"  # "seed" | "discovery"
    notes: str = ""


# --- Search results ----------------------------------------------------------


class CorpusHit(BaseModel):
    corpus_doc_id: str
    title: str = ""
    quote: str = ""
    relevance_score: float = 0.0
    domain: ResearcherDomain = "legal"

    def to_brief_citation(self) -> BriefCitation:
        return BriefCitation(
            corpus_doc_id=self.corpus_doc_id,
            title=self.title,
            quote=self.quote,
            relevance_score=self.relevance_score,
        )


@runtime_checkable
class CorpusStore(Protocol):
    """Retrieval contract researchers depend on, backend-agnostic."""

    def search(
        self, domain: ResearcherDomain, query: str, top_k: int = 3
    ) -> list[CorpusHit]: ...

    def list_domains(self) -> list[str]: ...


# --- Local backend (BM25 over files) ----------------------------------------

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")


def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def _title_for(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return fallback


def _best_quote(text: str, query_tokens: set[str]) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return text[:350].strip()
    best = max(
        paragraphs,
        key=lambda p: len(set(_tokenize(p)) & query_tokens),
    )
    return " ".join(best.split())[:700]


class LocalCorpusStore:
    """BM25 over ``<corpus_dir>/<subdir>/**.md``. Offline; no credentials."""

    def __init__(self, corpus_dir: Path | None = None) -> None:
        self.corpus_dir = corpus_dir or CORPUS_DIR

    def _subdir(self, domain: ResearcherDomain) -> Path:
        return self.corpus_dir / DOMAIN_SUBDIR.get(domain, domain)

    def _load(self, domain: ResearcherDomain) -> list[tuple[Path, str]]:
        root = self._subdir(domain)
        if not root.exists():
            return []
        return [
            (p, p.read_text(encoding="utf-8")) for p in sorted(root.rglob("*.md"))
        ]

    def list_domains(self) -> list[str]:
        if not self.corpus_dir.exists():
            return []
        return sorted(
            p.name for p in self.corpus_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
        )

    def search(
        self, domain: ResearcherDomain, query: str, top_k: int = 3
    ) -> list[CorpusHit]:
        docs = self._load(domain)
        if not docs:
            return []
        tokenized = [_tokenize(content) for _, content in docs]
        bm25 = BM25Okapi(tokenized)
        query_tokens = _tokenize(query)
        scores = bm25.get_scores(query_tokens)
        ranked = sorted(
            zip(docs, scores, strict=True),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        query_token_set = set(query_tokens)
        hits: list[CorpusHit] = []
        for (path, content), score in ranked[: max(1, min(top_k, len(ranked)))]:
            hits.append(
                CorpusHit(
                    corpus_doc_id=path.name,
                    title=_title_for(content, path.stem.replace("_", " ").title()),
                    quote=_best_quote(content, query_token_set),
                    relevance_score=round(float(score), 4),
                    domain=domain,
                )
            )
        return hits
