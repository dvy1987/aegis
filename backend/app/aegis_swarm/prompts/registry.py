"""Prompt registry for the swarm agents.

Every agent's prompt is an individually-loadable, versioned **component**. This
is the seam that makes per-agent credit assignment possible (Learning
Coordinator, Phase 6): a weakness attributed to dimension X routes to the
responsible agent's prompt component, which can be swapped/evolved independently
- mirroring how Part A loads ``drafter_v2``.

Prompts live next to this file as ``<role>_v<N>.md``. ``CURRENT_VERSIONS`` pins
the active version per role; bump it on promotion (and register as a Phoenix
Prompt).

**Weak-v1 demo scaffold (PRD 15.5, Phase 3).** A configurable set of agents
(``WEAK_V1_AGENTS``) ships with a deliberately weak ``<role>_v1_weak.md`` pinned
as the active baseline. This guarantees visible self-improvement headroom. The
weak set is a **dial**: add/remove a role here (and drop a matching ``_v1_weak.md``).
SAFETY is never weakened - only quality dimensions. The design rationale lives in
``prompts/WEAK_BASELINES.md`` (NOT a runtime prompt; never sent to a model).

**Evolution integrity.** The strong reference prompts live in ``prompts/targets/``
and are a **human evaluation ceiling, NEVER an optimizer input**. They are NOT
loadable as a registry version (``available_versions`` does not list them), so a
Phase 6 seeding step cannot read them. The optimizer seeds only from
``current_version`` (the weak baseline) and success is held-out lift vs that
baseline - not similarity to the target. See ``WEAK_BASELINES.md``.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

PROMPTS_DIR = Path(__file__).resolve().parent

AGENT_ROLES: tuple[str, ...] = (
    "orchestrator",
    "triage",
    "insurer_intelligence",
    "policy_detective",
    "medical_necessity",
    "legal_researcher",
    "precedent_miner",
    "strategist",
    "drafter",
    "adversarial_reviewer",
)

# Agents that START on a deliberately weak baseline (PRD 15.5 demo scaffold).
# Each must have a ``<role>_v1_weak.md`` on disk; the strong ``<role>_v1.md`` is
# the evolved target. This is a DIAL - the recommended trio owns 0.75 of the
# weighted composite across three distinct, non-overlapping quality dimensions
# (drafter: grounding+coherence; strategist: appeal_vector+evidence_completeness;
# medical_necessity: case_specific_clinical_rebuttal), so the demo lift is large
# AND cleanly attributable per agent. See docs/architecture/credit-assignment-map.md.
WEAK_V1_AGENTS: tuple[str, ...] = (
    "drafter",
    "strategist",
    "medical_necessity",
)

_WEAK_VERSION: str = "v1_weak"

# Strong reference prompts (the human evaluation ceiling) live here, OUTSIDE the
# loadable ``<role>_v*.md`` version namespace, so the optimizer cannot read them.
TARGETS_DIR = PROMPTS_DIR / "targets"

# Active prompt version per role. Bump on promotion. Agents in WEAK_V1_AGENTS are
# pinned to their weak baseline; everyone else starts strong at v1.
CURRENT_VERSIONS: dict[str, str] = {
    role: (_WEAK_VERSION if role in WEAK_V1_AGENTS else "v1") for role in AGENT_ROLES
}

_VERSION_RE = re.compile(r"_v([0-9A-Za-z_]+)\.md$")


class PromptComponent(BaseModel):
    """A loadable, versioned prompt - the credit-assignment unit.

    ``component_id`` is the agent role; ``kind`` is ``prompt`` to match the
    Learning Coordinator's ``Component`` contract.
    """

    component_id: str
    kind: str = "prompt"
    version: str
    text: str


def _require_role(role: str) -> None:
    if role not in AGENT_ROLES:
        raise KeyError(f"unknown swarm agent role: {role!r}")


def prompt_path(role: str, version: str | None = None) -> Path:
    _require_role(role)
    version = version or CURRENT_VERSIONS[role]
    return PROMPTS_DIR / f"{role}_{version}.md"


def current_version(role: str) -> str:
    _require_role(role)
    return CURRENT_VERSIONS[role]


def is_weak_agent(role: str) -> bool:
    """True if ``role`` ships on the deliberately weak demo baseline (PRD 15.5)."""
    _require_role(role)
    return role in WEAK_V1_AGENTS


def weak_agents() -> list[str]:
    return list(WEAK_V1_AGENTS)


def _target_path(role: str) -> Path:
    return TARGETS_DIR / f"{role}.md"


def has_target_reference(role: str) -> bool:
    """True if a quarantined strong-reference prompt exists for ``role``."""
    _require_role(role)
    return _target_path(role).exists()


def load_target_reference(role: str) -> str:
    """Load the strong reference prompt (the human evaluation CEILING).

    This is intentionally NOT part of the loadable version namespace and MUST
    NEVER be used as an optimizer seed - it exists only for human/eval comparison
    ("how much of the gap to the hand-written reference did the loop recover?").
    Reading it inside the Learning Coordinator's reflection/mutation path would be
    a search-integrity violation. See ``WEAK_BASELINES.md``.
    """
    _require_role(role)
    path = _target_path(role)
    if not path.exists():
        raise FileNotFoundError(f"no strong-reference target for role={role!r}: {path}")
    return path.read_text(encoding="utf-8")


def available_versions(role: str) -> list[str]:
    """Versions present on disk for ``role`` (e.g. ['v1', 'v1_weak', 'v2'])."""
    _require_role(role)
    out: list[str] = []
    for path in PROMPTS_DIR.glob(f"{role}_v*.md"):
        match = _VERSION_RE.search(path.name)
        if match:
            out.append(f"v{match.group(1)}")
    return sorted(out)


def load_prompt(role: str, version: str | None = None) -> str:
    """Load an agent's system prompt text. Defaults to the pinned current version."""
    path = prompt_path(role, version)
    if not path.exists():
        raise FileNotFoundError(
            f"prompt not found for role={role!r} version={version or CURRENT_VERSIONS[role]!r}: {path}"
        )
    return path.read_text(encoding="utf-8")


def load_component(role: str, version: str | None = None) -> PromptComponent:
    version = version or CURRENT_VERSIONS[role]
    return PromptComponent(
        component_id=role, version=version, text=load_prompt(role, version)
    )


def list_components() -> list[PromptComponent]:
    """All currently-active agent prompt components (one per role)."""
    return [load_component(role) for role in AGENT_ROLES]
