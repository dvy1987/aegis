"""Inject per-role prompt overrides into a ``SwarmAgentClient`` (live experiments)."""

from __future__ import annotations

from typing import Any

from app.aegis_swarm.client import SwarmAgentClient
from app.aegis_swarm.corpus_store import CorpusHit
from app.aegis_swarm.schemas import (
    AdversarialCritique,
    AppealStrategy,
    InsurerBrief,
    ResearchBrief,
    ResearchDepth,
    ResearcherName,
    RoutingManifest,
)


class PromptOverrideSwarmClient:
    """Delegates to a base client; ``GeminiSwarmClient`` reads overrides per role."""

    name = "prompt_override_swarm"

    def __init__(
        self,
        base: SwarmAgentClient,
        overrides: dict[str, str],
    ) -> None:
        self._base = base
        self._overrides = dict(overrides)
        if hasattr(base, "prompt_overrides"):
            base.prompt_overrides = dict(overrides)  # type: ignore[attr-defined]

    def triage(self, parsed_case: dict[str, Any]) -> RoutingManifest:
        return self._base.triage(parsed_case)

    def research(
        self,
        agent: ResearcherName,
        parsed_case: dict[str, Any],
        depth: ResearchDepth,
        hits: list[CorpusHit],
        phoenix_summary: dict[str, Any] | None = None,
    ) -> ResearchBrief:
        return self._base.research(agent, parsed_case, depth, hits, phoenix_summary)

    def strategize(
        self,
        parsed_case: dict[str, Any],
        briefs: list[ResearchBrief],
        manifest: RoutingManifest,
        playbook: dict[str, Any],
    ) -> AppealStrategy:
        return self._base.strategize(parsed_case, briefs, manifest, playbook)

    def draft(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        citations: list[CorpusHit],
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        critique: AdversarialCritique | None = None,
    ) -> str:
        return self._base.draft(
            parsed_case, strategy, citations, playbook, phoenix_summary, critique
        )

    def critique(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        letter: str,
        iteration: int = 1,
    ) -> AdversarialCritique:
        return self._base.critique(parsed_case, strategy, letter, iteration)
