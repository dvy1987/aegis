"""Deterministic tool seam for the swarm.

The swarm's *non-LLM* work (corpus retrieval, playbook load, Phoenix-memory
lookup) lives here, mirroring Part A's ``aegis_v1.tools``. The LLM-driven
reasoning steps go through the injectable ``SwarmAgentClient`` (``client.py``).

Playbook + Phoenix lookups REUSE Part A's tools unchanged so the swarm shares
the same promoted playbooks and the same Phoenix-memory contract (and so the
Learning Coordinator sees one surface, not two). Retrieval goes through the
``CorpusStore`` seam (ADR-007) instead of Part A's flat BM25 so each researcher
retrieves over its own domain subtree.
"""

from __future__ import annotations

from typing import Any

from app.aegis_swarm.prompts import registry
from app.aegis_swarm.corpus_store import CorpusHit, CorpusStore, LocalCorpusStore
from app.aegis_swarm.schemas import (
    AgentTraceSignal,
    ResearchDepth,
    ResearcherDomain,
    ResearcherInvocation,
    ResearcherName,
)
from app.aegis_v1.tools import phoenix_mcp_lookup as _v1_phoenix_mcp_lookup
from app.aegis_v1.tools import playbook_loader as _v1_playbook_loader

# Which quality dimension(s) each agent's prompt PRIMARILY owns (inverted from
# docs/architecture/credit-assignment-map.md). The per-agent trace signal stamps
# these so credit assignment (Phase 6) can route a weak dimension to the right
# agent. Keep in sync with the credit map when the topology's responsibilities
# change (credit-map invariant: "map is versioned with the topology").
AGENT_OWNED_DIMENSIONS: dict[str, list[str]] = {
    "drafter": ["grounding", "persuasive_coherence"],
    "strategist": ["appeal_vector_capture", "evidence_completeness"],
    "medical_necessity": ["case_specific_clinical_rebuttal"],
}

# Each researcher retrieves over one corpus domain. Policy Detective reads the
# insurer subtree (plan/policy docs are insurer-published) - see DOMAIN_SUBDIR.
RESEARCHER_DOMAIN: dict[ResearcherName, ResearcherDomain] = {
    "medical_necessity": "clinical",
    "legal_researcher": "legal",
    "policy_detective": "policy",
    "insurer_intelligence": "insurer",
    "precedent_miner": "precedent",
}

# Triage depth knob -> number of corpus hits to pull (brief/standard/deep).
_DEPTH_TOP_K: dict[ResearchDepth, int] = {"brief": 1, "standard": 3, "deep": 5}

# Denial type -> the specialist researchers it routes to, from the Triage prompt's
# routing table (``triage_v1.md``). ``insurer_intelligence`` is ALWAYS appended
# (load-bearing for the Phoenix MCP demo, never skipped) and ``precedent_miner``
# is added on complexity 5. The keys are the swarm's 7-type denial vocabulary.
DENIAL_ROUTING: dict[str, list[ResearcherName]] = {
    "medical_necessity": ["medical_necessity", "policy_detective"],
    "prior_auth_missing": ["policy_detective", "legal_researcher"],
    "step_therapy": ["medical_necessity"],
    "experimental_investigational": ["medical_necessity", "legal_researcher"],
    "out_of_network": ["legal_researcher", "policy_detective"],
    "coding_error": ["policy_detective"],
    "coverage_exclusion": ["policy_detective", "legal_researcher"],
}

# Complexity score (1/3/5) -> per-researcher retrieval depth (Triage prompt).
_COMPLEXITY_DEPTH: dict[int, ResearchDepth] = {1: "brief", 3: "standard", 5: "deep"}

# States with aggressive parity / IRO regimes that push a case to "complex"
# (Triage prompt: state-law-sensitive -> complexity 5, full fan-out).
_COMPLEX_STATES: frozenset[str] = frozenset({"CA", "NY", "MA"})


def depth_to_top_k(depth: ResearchDepth) -> int:
    return _DEPTH_TOP_K.get(depth, 3)


def estimate_complexity(parsed_case: dict[str, Any]) -> int:
    """Deterministic 1/3/5 complexity for the stub Triage (no playbook access).

    Mirrors the Triage prompt's signals that survive offline: state-law
    sensitivity, a secondary denial type, or multiple denial reasons push to 5
    (deep + full fan-out incl. Precedent Miner); the routine default is 3.
    """
    reason = str(parsed_case.get("cited_denial_reason", "")).lower()
    state = str(parsed_case.get("state", "") or "").upper()
    if state in _COMPLEX_STATES:
        return 5
    if parsed_case.get("denial_type_secondary"):
        return 5
    if ";" in reason or " and also " in reason:
        return 5
    return 3


def complexity_to_depth(complexity: int) -> ResearchDepth:
    return _COMPLEXITY_DEPTH.get(complexity, "standard")


def build_routing(denial_type: str, complexity: int) -> list[ResearcherInvocation]:
    """Build the per-researcher invocation list from the denial-type routing table.

    ``insurer_intelligence`` is always invoked (Phoenix-load-bearing); the
    Precedent Miner is added when complexity is 5. Depth follows complexity. The
    Gemini Triage may diverge case-by-case; this is the deterministic default the
    stub uses and the live client falls back to.
    """
    depth = complexity_to_depth(complexity)
    names: list[ResearcherName] = list(DENIAL_ROUTING.get(denial_type, ["medical_necessity"]))
    names.append("insurer_intelligence")
    if complexity == 5 and "precedent_miner" not in names:
        names.append("precedent_miner")
    ordered = list(dict.fromkeys(names))  # dedupe, preserve order
    invocations: list[ResearcherInvocation] = []
    for name in ordered:
        reason = (
            "always invoked; Phoenix-MCP load-bearing"
            if name == "insurer_intelligence"
            else f"routed for {denial_type} (complexity {complexity})"
        )
        invocations.append(
            ResearcherInvocation(name=name, depth=depth, invoke=True, reason=reason)
        )
    return invocations


def build_research_query(parsed_case: dict[str, Any]) -> str:
    """Same query construction Part A's pipeline uses, shared across researchers."""
    return " ".join(
        str(parsed_case.get(field, ""))
        for field in (
            "insurer",
            "denial_type",
            "service_or_procedure",
            "diagnosis_summary",
            "cited_denial_reason",
        )
    ).strip()


def corpus_search(
    store: CorpusStore | None,
    domain: ResearcherDomain,
    query: str,
    top_k: int = 3,
) -> list[CorpusHit]:
    """Retrieve traceable corpus hits for one researcher domain via the store."""
    active = store or LocalCorpusStore()
    return active.search(domain, query, top_k=top_k)


def get_learned_playbook(insurer: str, denial_type: str) -> dict[str, Any]:
    """Load the promoted playbook for this slice. Reuses Part A's loader so the
    swarm and Part A share one playbook surface (the Strategist confirms the
    version the Insurer Intelligence researcher referenced)."""
    return _v1_playbook_loader(insurer, denial_type)


def swarm_phoenix_lookup(
    insurer: str,
    denial_type: str,
    case_id: str = "interactive_case",
) -> dict[str, Any]:
    """Phoenix-memory context for the Insurer Intelligence researcher. Reuses
    Part A's lookup so the MCP-off counterfactual (Phase 5) behaves identically:
    ``PHOENIX_MCP_ENABLED=false`` -> ``status='disabled'``."""
    return _v1_phoenix_mcp_lookup(insurer, denial_type, case_id)


def agent_owned_dimensions(role: str) -> list[str]:
    return list(AGENT_OWNED_DIMENSIONS.get(role, []))


def make_agent_trace_signal(
    role: str,
    *,
    status: str = "",
    finding_count: int = 0,
    citation_count: int = 0,
    risk_flags: list[str] | None = None,
    summary: str = "",
) -> AgentTraceSignal:
    """Build ONE firewall-safe per-agent trace signal (FR-5 credit assignment).

    Carries only laundered, structural fields: the agent role, its pinned
    prompt_version (the credit-assignment unit), whether it ran on the weak demo
    baseline, the dimension(s) it owns, counts/flags, and a templated summary.
    Callers MUST pass a ``summary`` built from safe primitives only - NEVER raw
    letter text, brief quotes, agent ``thinking``, PHI, or answer-key fields.
    """
    return AgentTraceSignal(
        role=role,
        prompt_version=registry.current_version(role),
        is_weak_v1=registry.is_weak_agent(role),
        owned_dimensions=agent_owned_dimensions(role),
        status=status,
        finding_count=finding_count,
        citation_count=citation_count,
        risk_flags=sorted(set(risk_flags or [])),
        summary=summary,
    )
