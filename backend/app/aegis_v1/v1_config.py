from __future__ import annotations

import os
from typing import Any

from app.aegis_v1.planner_refinement_client import (
    GeminiPlannerRefinementClient,
    PlannerRefinementClient,
    StubPlannerRefinementClient,
)
from app.aegis_swarm.corpus_store import CorpusStore, LocalCorpusStore
from app.aegis_swarm.literature_discovery import DiscoveryConfig, LiteratureDiscovery
from app.aegis_swarm.vertex_discovery import build_discovery_search_client
from app.aegis_swarm.vertex_search import (
    VertexSearchCorpusStore,
    build_cloud_only_corpus_store,
)

V1_MAX_DISCOVERY_FETCHES = 5


def v1_mode() -> str:
    return os.environ.get("AEGIS_V1_MODE", "stub").lower()


def build_v1_refinement_client() -> PlannerRefinementClient:
    if v1_mode() == "live":
        return GeminiPlannerRefinementClient()
    return StubPlannerRefinementClient()


def build_v1_discovery(
    corpus_dir=None, *, discovery_enabled: bool | None = None
) -> LiteratureDiscovery:
    base = DiscoveryConfig.from_env()
    enabled = base.enabled if discovery_enabled is None else discovery_enabled
    config = DiscoveryConfig(
        enabled=enabled,
        per_case_cap=V1_MAX_DISCOVERY_FETCHES,
        per_day_cap=base.per_day_cap,
    )
    return LiteratureDiscovery(
        corpus_dir=corpus_dir,
        search_client=build_discovery_search_client(),
        config=config,
    )


def build_v1_corpus_store(corpus_dir=None) -> CorpusStore:
    # PM decision (2026-06-02): cloud library is source of truth; do not fall
    # back to local disk. If Vertex isn't configured, retrieval returns empty
    # and the app surfaces "library unavailable".
    return build_cloud_only_corpus_store(corpus_dir)


def build_v1_library_stack(
    corpus_dir=None, *, discovery_enabled: bool | None = None
) -> dict[str, Any]:
    store = build_v1_corpus_store(corpus_dir)
    uses_vertex = isinstance(store, VertexSearchCorpusStore)
    return {
        "corpus_store": store,
        # Discovery is an explicit user-requested behavior (API flag). We do not
        # silently disable it; callers should surface an error if discovery is
        # requested but the cloud library is unavailable.
        "discovery": build_v1_discovery(corpus_dir, discovery_enabled=discovery_enabled),
        "refinement_client": build_v1_refinement_client(),
        "uses_vertex_store": uses_vertex,
    }
