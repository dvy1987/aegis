"""Build swarm ``Candidate`` seeds from the prompt registry (evolution integrity)."""

from __future__ import annotations

from app.aegis_swarm.prompts import registry
from app.learning.credit_resolution import EVOLVABLE_AGENT_ROLES
from app.learning.models import Candidate, Component


def swarm_seed_candidate(*, candidate_id: str = "seed") -> Candidate:
    """Seed from ``registry.current_version`` for every evolvable pipeline agent.

    Never reads ``load_target_reference()`` — strong prompts are human ceilings only.
    """
    components: dict[str, Component] = {}
    for role in EVOLVABLE_AGENT_ROLES:
        version = registry.current_version(role)
        components[role] = Component(
            component_id=role,
            kind="prompt",
            version=version,
            text=registry.load_prompt(role, version),
        )
    return Candidate(candidate_id=candidate_id, components=components, origin="seed")


def prompt_overrides_from_candidate(candidate: Candidate) -> dict[str, str]:
    """Map role -> prompt text for ``PromptOverrideSwarmClient``."""
    return {
        role: comp.text or ""
        for role, comp in candidate.components.items()
        if comp.kind == "prompt" and comp.text
    }
