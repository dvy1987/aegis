from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.aegis_v1.corpus_bridge import (
    hits_to_retrieval,
    library_is_thin,
    search_unified_library,
)

logger = logging.getLogger(__name__)
from app.aegis_v1.planner_refinement_client import PlannerRefinementClient
from app.aegis_v1.schemas import CitationHit, ParsedCase
from app.aegis_v1.search_planner import (
    CURRENT_SEARCH_PLANNER_VERSION,
    build_baseline_query,
    discovery_domain_for_denial,
    refine_discovery_query,
)
from app.aegis_v1.v1_config import V1_MAX_DISCOVERY_FETCHES
from app.aegis_swarm.corpus_store import CorpusStore
from app.aegis_swarm.literature_discovery import LiteratureDiscovery


class LibraryPrepMetadata(BaseModel):
    search_planner_version: str = CURRENT_SEARCH_PLANNER_VERSION
    library_search_query: str = ""
    library_available: bool = True
    cloud_library_used: bool = False
    discovery_enabled: bool = False
    discovery_ran: bool = False
    discovery_fetch_count: int = 0
    discovery_queries: list[str] = Field(default_factory=list)
    discovery_ingested_count: int = 0
    discovery_rejected_count: int = 0
    layer3_refinement_ran: bool = False
    layer3_refinement_rejected: bool = False


class LibraryContext(BaseModel):
    retrieval: dict[str, Any]
    metadata: LibraryPrepMetadata
    risk_flags: list[str] = Field(default_factory=list)


def _citation_hits(retrieval: dict[str, Any]) -> list[CitationHit]:
    return [CitationHit.model_validate(h) for h in retrieval.get("hits", [])]


def degraded_library_context(
    query: str = "", *, reason: str = "library_error_degraded"
) -> LibraryContext:
    """A safe, empty library context for when the library is offline or errors.

    The library is never on the critical path: callers degrade to this (no
    citations + a risk flag) so a failed search/discovery cannot break drafting
    or the showcase optimization loop.
    """
    return LibraryContext(
        retrieval=hits_to_retrieval(query, []),
        metadata=LibraryPrepMetadata(
            library_search_query=query, library_available=False
        ),
        risk_flags=[reason],
    )


def prepare_library_context(
    parsed: dict[str, Any] | ParsedCase,
    *,
    case_id: str,
    corpus_store: CorpusStore,
    discovery: LiteratureDiscovery | None = None,
    refinement_client: PlannerRefinementClient | None = None,
    cloud_library_used: bool = False,
) -> LibraryContext:
    """Pre-flight library search + optional surgical discovery (spec FR-1–FR-13)."""
    case = parsed if isinstance(parsed, ParsedCase) else ParsedCase.model_validate(parsed)
    discovery = discovery or LiteratureDiscovery()
    meta = LibraryPrepMetadata(
        discovery_enabled=discovery.config.enabled,
        cloud_library_used=cloud_library_used,
    )
    risk_flags: list[str] = []

    baseline = build_baseline_query(case.model_dump())
    meta.library_search_query = baseline

    # Baseline retrieval must never crash drafting/optimization: degrade to no
    # citations + a risk flag if the (cloud or local) library search throws.
    try:
        hits = search_unified_library(corpus_store, baseline, top_k=3)
    except Exception:
        logger.warning(
            "library baseline search failed for case_id=%s; degrading to no citations",
            case_id,
            exc_info=True,
        )
        hits = []
        meta.library_available = False
        risk_flags.append("library_search_error")
    if not hits and not cloud_library_used:
        meta.library_available = False
        risk_flags.append("library_unavailable_no_cloud_index")
    retrieval = hits_to_retrieval(baseline, hits)

    if library_is_thin(case, _citation_hits(retrieval)):
        if not discovery.config.enabled:
            risk_flags.append("library_thin_no_discovery")
        else:
            domain = discovery_domain_for_denial(case.denial_type)
            meta.discovery_ran = True
            discovery_queries: list[str] = []
            total_ingested = 0
            total_rejected = 0

            # Discovery is best-effort: a failed fetch/refine must not lose the
            # baseline retrieval or break the run.
            try:
                for fetch_idx in range(V1_MAX_DISCOVERY_FETCHES):
                    if not library_is_thin(case, _citation_hits(retrieval)):
                        break

                    if fetch_idx == 0:
                        query = baseline
                    else:
                        query, layer3_ran = refine_discovery_query(
                            parsed_case=case.model_dump(),
                            fetch_index=fetch_idx,
                            prior_queries=discovery_queries,
                            hit_count=len(retrieval["hits"]),
                            ingest_count=total_ingested,
                            reject_count=total_rejected,
                            client=refinement_client,
                        )
                        if layer3_ran:
                            meta.layer3_refinement_ran = True

                    discovery_queries.append(query)
                    meta.discovery_fetch_count += 1
                    result = discovery.maybe_discover(domain, query, case_id, limit=1)
                    total_ingested += len(result.ingested)
                    total_rejected += len(result.rejected)

                    hits = search_unified_library(corpus_store, baseline, top_k=3)
                    retrieval = hits_to_retrieval(baseline, hits)
            except Exception:
                logger.warning(
                    "library discovery failed for case_id=%s; keeping baseline retrieval",
                    case_id,
                    exc_info=True,
                )
                risk_flags.append("library_discovery_error")

            meta.discovery_queries = discovery_queries
            meta.discovery_ingested_count = total_ingested
            meta.discovery_rejected_count = total_rejected

            if library_is_thin(case, _citation_hits(retrieval)):
                risk_flags.append("library_thin_after_discovery")

    return LibraryContext(
        retrieval=retrieval,
        metadata=meta,
        risk_flags=risk_flags,
    )
