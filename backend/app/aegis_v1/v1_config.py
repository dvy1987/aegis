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
from app.aegis_swarm.vertex_search import VertexSearchCorpusStore, build_corpus_store

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
    return build_corpus_store(corpus_dir)


def build_v1_library_stack(
    corpus_dir=None, *, discovery_enabled: bool | None = None
) -> dict[str, Any]:
    store = build_v1_corpus_store(corpus_dir)
    return {
        "corpus_store": store,
        "discovery": build_v1_discovery(corpus_dir, discovery_enabled=discovery_enabled),
        "refinement_client": build_v1_refinement_client(),
        "uses_vertex_store": isinstance(store, VertexSearchCorpusStore),
    }
