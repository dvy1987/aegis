"""Live Vertex grounded-search backend for LiteratureDiscovery (Phase 4).

Swapped in when ``AEGIS_VERTEX_DISCOVERY=true``. Offline tests keep
``FakeDiscoverySearchClient``. Results are still gated by the full
``LiteratureDiscovery`` pipeline (sanitize -> trust-tier -> ingest).
"""

from __future__ import annotations

import logging
import os
import re

from app.aegis_swarm.literature_discovery import DiscoveryCandidate, DiscoverySearchClient
from app.aegis_swarm.schemas import ResearcherDomain

_LOG = logging.getLogger(__name__)
_URL_RE = re.compile(r"https?://[^\s\])<>\"']+")


def vertex_discovery_enabled() -> bool:
    return os.environ.get("AEGIS_VERTEX_DISCOVERY", "false").lower() in (
        "1",
        "true",
        "yes",
    )


class VertexGroundedDiscoveryClient:
    """Gemini + Google Search grounding -> ``DiscoveryCandidate`` list.

    Construction is offline-safe; ``search`` needs Vertex credentials and is
    exercised in a GCP integration session. On failure returns ``[]`` so the
    pipeline can continue with the existing corpus only.
    """

    def __init__(
        self,
        model: str | None = None,
        location: str | None = None,
    ) -> None:
        self.model = model or os.environ.get("AEGIS_SWARM_MODEL", "gemini-2.5-flash")
        self.location = location or os.environ.get(
            "GOOGLE_CLOUD_LOCATION", "us-central1"
        )

    def search(
        self, domain: ResearcherDomain, query: str, limit: int = 5
    ) -> list[DiscoveryCandidate]:
        try:
            return self._search_live(domain, query, limit)
        except Exception:
            _LOG.warning(
                "VertexGroundedDiscoveryClient.search failed; returning no candidates",
                exc_info=True,
            )
            return []

    def _search_live(
        self, domain: ResearcherDomain, query: str, limit: int
    ) -> list[DiscoveryCandidate]:
        from google import genai
        from google.genai import types

        prompt = (
            f"Find up to {limit} authoritative sources relevant to this health-insurance "
            f"appeal research query. Return a short bullet per source with title, URL, and "
            f"a one-sentence snippet. Domain focus: {domain}.\n\nQuery: {query}"
        )
        client = genai.Client(vertexai=True, location=self.location)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = response.text or ""
        return _parse_candidates(text, domain)[:limit]


def _parse_candidates(text: str, domain: ResearcherDomain) -> list[DiscoveryCandidate]:
    """Best-effort parse of grounded search prose into structured candidates."""
    candidates: list[DiscoveryCandidate] = []
    blocks = re.split(r"\n\s*[-*•]\s+", text)
    if len(blocks) <= 1:
        blocks = [ln for ln in text.splitlines() if ln.strip()]
    for block in blocks:
        chunk = block.strip()
        if not chunk:
            continue
        urls = _URL_RE.findall(chunk)
        if not urls:
            continue
        title = chunk.split(urls[0])[0].strip(" :–-") or "Discovered source"
        snippet = chunk.replace(urls[0], "").strip(" :–-") or title
        candidates.append(
            DiscoveryCandidate(
                title=title[:200],
                source_url=urls[0],
                snippet=snippet[:2000],
                domain=domain,
            )
        )
    return candidates


def build_discovery_search_client() -> DiscoverySearchClient:
    """Offline fake by default; live Vertex grounding when explicitly enabled."""
    from app.aegis_swarm.literature_discovery import FakeDiscoverySearchClient

    if vertex_discovery_enabled():
        return VertexGroundedDiscoveryClient()
    return FakeDiscoverySearchClient()
