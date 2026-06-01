"""Live vs offline wiring for the swarm (Phase 4).

Central factory so ``agent.py``, ``appeal_api.py``, and deploy scripts share one
configuration surface. Defaults stay credential-free (stub client, local corpus,
fake discovery).
"""

from __future__ import annotations

import os
from typing import Any

from app.aegis_swarm.client import GeminiSwarmClient, StubSwarmClient, SwarmAgentClient
from app.aegis_swarm.corpus_store import CorpusStore, LocalCorpusStore
from app.aegis_swarm.literature_discovery import LiteratureDiscovery
from app.aegis_swarm.vertex_discovery import build_discovery_search_client
from app.aegis_swarm.vertex_search import build_corpus_store


def swarm_mode() -> str:
    """``stub`` (offline default) or ``live`` (Vertex/Gemini)."""
    return os.environ.get("AEGIS_SWARM_MODE", "stub").lower()


def build_swarm_client() -> SwarmAgentClient:
    if swarm_mode() == "live":
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        return GeminiSwarmClient(location=location)
    return StubSwarmClient()


def build_literature_discovery(
    corpus_dir=None,
) -> LiteratureDiscovery:
    return LiteratureDiscovery(
        corpus_dir=corpus_dir,
        search_client=build_discovery_search_client(),
    )


def build_live_stack(corpus_dir=None) -> dict[str, Any]:
    """Wire client + corpus + discovery for one pipeline run."""
    store = build_corpus_store(corpus_dir)
    return {
        "client": build_swarm_client(),
        "corpus_store": store,
        "discovery": build_literature_discovery(corpus_dir),
    }


def default_corpus_store() -> CorpusStore:
    return build_corpus_store()
