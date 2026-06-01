"""Vertex AI Search corpus backend (ADR-007, Phase 4).

``VertexSearchCorpusStore`` implements the ``CorpusStore`` Protocol with an
injectable search backend. Offline tests and unconfigured environments use
``LocalCorpusStore`` via the factory; live runs use ``DiscoveryEngineVertexBackend``
when ``VERTEX_SEARCH_DATA_STORE_ID`` is set.

On Vertex API failure the store falls back to local BM25 so a live demo does not
hard-fail mid-run (same posture as ``GeminiSwarmClient`` stub-fallback).
"""

from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

from app.aegis_swarm.corpus_store import (
    CORPUS_DIR,
    DOMAIN_SUBDIR,
    CorpusHit,
    LocalCorpusStore,
    _best_quote,
    _title_for,
    _tokenize,
)
from app.aegis_swarm.schemas import ResearcherDomain

_LOG = logging.getLogger(__name__)


def vertex_search_configured() -> bool:
    """True when the minimal Vertex AI Search env is present."""
    return bool(os.environ.get("VERTEX_SEARCH_DATA_STORE_ID", "").strip())


def vertex_search_settings() -> dict[str, str]:
    """Resolved Vertex AI Search settings (empty strings when unset)."""
    return {
        "project": os.environ.get("VERTEX_SEARCH_PROJECT", os.environ.get("GOOGLE_CLOUD_PROJECT", "")),
        "location": os.environ.get("VERTEX_SEARCH_LOCATION", "global"),
        "data_store_id": os.environ.get("VERTEX_SEARCH_DATA_STORE_ID", ""),
        "serving_config": os.environ.get("VERTEX_SEARCH_SERVING_CONFIG", "default_config"),
    }


@runtime_checkable
class VertexSearchBackend(Protocol):
    """Credential-gated search contract. Swapped for fakes in unit tests."""

    def search(
        self, domain: ResearcherDomain, query: str, top_k: int
    ) -> list[CorpusHit]: ...


class LocalDelegatingVertexBackend:
    """Offline / fallback backend: same BM25 retrieval as ``LocalCorpusStore``."""

    def __init__(self, corpus_dir=None) -> None:
        self._local = LocalCorpusStore(corpus_dir)

    def search(
        self, domain: ResearcherDomain, query: str, top_k: int
    ) -> list[CorpusHit]:
        return self._local.search(domain, query, top_k=top_k)


class DiscoveryEngineVertexBackend:
    """Live Vertex AI Search (Discovery Engine) backend.

    Expects corpus documents indexed with a ``domain`` struct field (or a URI
    path containing the domain subdir name). Construction is unit-tested offline;
    live search is exercised in a GCP integration session.
    """

    def __init__(
        self,
        project: str,
        location: str,
        data_store_id: str,
        serving_config: str = "default_config",
    ) -> None:
        if not project or not data_store_id:
            raise ValueError("project and data_store_id are required for Vertex search")
        self.project = project
        self.location = location
        self.data_store_id = data_store_id
        self.serving_config = serving_config

    @classmethod
    def from_env(cls) -> "DiscoveryEngineVertexBackend":
        settings = vertex_search_settings()
        return cls(
            project=settings["project"],
            location=settings["location"],
            data_store_id=settings["data_store_id"],
            serving_config=settings["serving_config"],
        )

    def _serving_config_path(self, client) -> str:
        return client.serving_config_path(
            project=self.project,
            location=self.location,
            data_store=self.data_store_id,
            serving_config=self.serving_config,
        )

    def search(
        self, domain: ResearcherDomain, query: str, top_k: int
    ) -> list[CorpusHit]:
        from google.cloud import discoveryengine_v1 as discoveryengine

        client = discoveryengine.SearchServiceClient()
        request = discoveryengine.SearchRequest(
            serving_config=self._serving_config_path(client),
            query=query,
            page_size=max(1, top_k * 2),
        )
        response = client.search(request)
        query_tokens = set(_tokenize(query))
        hits: list[CorpusHit] = []
        subdir = DOMAIN_SUBDIR.get(domain, domain)
        for result in response.results:
            doc = result.document
            struct = dict(doc.struct_data) if doc.struct_data else {}
            derived = dict(doc.derived_struct_data) if doc.derived_struct_data else {}
            merged = {**derived, **struct}
            doc_id = (
                merged.get("doc_id")
                or merged.get("corpus_doc_id")
                or (doc.name.rsplit("/", 1)[-1] if doc.name else "unknown.md")
            )
            if not str(doc_id).endswith(".md"):
                doc_id = f"{doc_id}.md"
            body = merged.get("snippet") or merged.get("content") or merged.get("extractive_answers", "")
            if isinstance(body, list):
                body = body[0] if body else ""
            title = merged.get("title") or _title_for(str(body), str(doc_id))
            quote = merged.get("quote") or _best_quote(str(body), query_tokens)
            score = float(getattr(result, "ranking_score", 0.0) or 0.0)
            hit_domain = merged.get("domain", domain)
            resolved_domain = hit_domain if hit_domain in DOMAIN_SUBDIR else domain
            if str(doc_id).startswith(subdir) or f"/{subdir}/" in str(
                merged.get("uri", "")
            ):
                resolved_domain = domain
            hits.append(
                CorpusHit(
                    corpus_doc_id=str(doc_id),
                    title=str(title),
                    quote=str(quote)[:700],
                    relevance_score=round(score, 4),
                    domain=resolved_domain,
                )
            )
        domain_hits = [h for h in hits if h.domain == domain or subdir in h.corpus_doc_id]
        return (domain_hits or hits)[:top_k]


class VertexSearchCorpusStore:
    """``CorpusStore`` backed by Vertex AI Search with local BM25 fallback."""

    def __init__(
        self,
        backend: VertexSearchBackend,
        *,
        fallback: LocalCorpusStore | None = None,
        corpus_dir=None,
    ) -> None:
        self.backend = backend
        self.fallback = fallback or LocalCorpusStore(corpus_dir)

    def list_domains(self) -> list[str]:
        return self.fallback.list_domains()

    def search(
        self, domain: ResearcherDomain, query: str, top_k: int = 3
    ) -> list[CorpusHit]:
        if not vertex_search_configured():
            return self.fallback.search(domain, query, top_k=top_k)
        try:
            hits = self.backend.search(domain, query, top_k)
            if hits:
                return hits
        except Exception:
            _LOG.warning(
                "VertexSearchCorpusStore.search failed for domain=%s; using local BM25",
                domain,
                exc_info=True,
            )
        return self.fallback.search(domain, query, top_k=top_k)


def build_corpus_store(corpus_dir=None) -> LocalCorpusStore | VertexSearchCorpusStore:
    """Factory: Vertex store when configured, else plain local BM25."""
    root = corpus_dir or CORPUS_DIR
    fallback = LocalCorpusStore(root)
    if not vertex_search_configured():
        return fallback
    try:
        backend = DiscoveryEngineVertexBackend.from_env()
    except ValueError:
        _LOG.warning("Vertex search misconfigured; using LocalCorpusStore")
        return fallback
    return VertexSearchCorpusStore(backend, fallback=fallback, corpus_dir=root)
