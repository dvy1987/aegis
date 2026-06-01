"""Pydantic schemas for the Part B swarm.

Translated from the per-agent prompt contracts in
``backend/app/aegis_swarm/prompts/*_v1.md``. The swarm's *terminal* output reuses
Part A's ``aegis_v1.schemas.AppealPackage`` (so the judge panel, simulator,
recorder, firewall, and Learning Coordinator all work unchanged); the
swarm-internal artifacts below attach as a ``SwarmRunArtifacts`` sidecar.

The 5 research briefs share one ``ResearchBrief`` shape (a findings list +
traceable citations + evidence gaps); ``InsurerBrief`` extends it with the
Phoenix-derived tactic fields. Per-researcher specialization of *behavior*
lives in each ``run_<agent>()`` (Phase 2), not in divergent schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Denial types the Triage agent may emit (Part A: first two; Part B adds the rest).
SwarmDenialType = Literal[
    "medical_necessity",
    "prior_auth_missing",
    "step_therapy",
    "experimental_investigational",
    "out_of_network",
    "coding_error",
    "coverage_exclusion",
]

ResearcherName = Literal[
    "medical_necessity",
    "legal_researcher",
    "policy_detective",
    "insurer_intelligence",
    "precedent_miner",
]

ResearchDepth = Literal["brief", "standard", "deep"]

# The corpus domain each non-insurer researcher retrieves over (CorpusStore subdir).
ResearcherDomain = Literal["clinical", "legal", "policy", "precedent", "insurer"]


# --- Triage -----------------------------------------------------------------


class ResearcherInvocation(BaseModel):
    name: ResearcherName
    depth: ResearchDepth = "standard"
    invoke: bool = True
    reason: str = ""


class RoutingManifest(BaseModel):
    case_id: str
    denial_type: SwarmDenialType
    denial_type_secondary: str | None = None
    confidence: float = 0.0
    complexity_score: Literal[1, 3, 5] = 3
    complexity_reasoning: str = ""
    researchers: list[ResearcherInvocation] = Field(default_factory=list)
    evidence_quote: str = ""
    thinking: str = ""
    risk_flags: list[str] = Field(default_factory=list)

    def invoked(self) -> list[ResearcherName]:
        return [r.name for r in self.researchers if r.invoke]


# --- Research briefs ---------------------------------------------------------


class BriefCitation(BaseModel):
    """A citation a researcher pulled from the controlled corpus. ``corpus_doc_id``
    is the trace-back handle the Strategist/Drafter and self_check verify."""

    corpus_doc_id: str
    title: str = ""
    quote: str = ""
    relevance_score: float = 0.0


class ResearchFinding(BaseModel):
    summary: str
    citations: list[BriefCitation] = Field(default_factory=list)


class ResearchBrief(BaseModel):
    agent: ResearcherName
    case_id: str
    domain: ResearcherDomain
    status: Literal["full", "partial", "empty"] = "full"
    findings: list[ResearchFinding] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    thinking: str = ""
    risk_flags: list[str] = Field(default_factory=list)

    def all_citations(self) -> list[BriefCitation]:
        return [c for f in self.findings for c in f.citations]


class InsurerBrief(ResearchBrief):
    """Insurer Intelligence brief - the load-bearing Phoenix-MCP researcher.

    When Phoenix MCP is disabled/unavailable, ``tactic`` is empty and
    ``status`` is ``empty`` with ``phoenix_mcp_unavailable`` in ``risk_flags`` -
    the demo counterfactual.
    """

    agent: ResearcherName = "insurer_intelligence"
    domain: ResearcherDomain = "insurer"
    tactic: str = ""
    success_patterns: list[str] = Field(default_factory=list)
    failure_patterns: list[str] = Field(default_factory=list)
    playbook_version: str | None = None
    similar_trace_count: int = 0


# --- Strategy ---------------------------------------------------------------


class StrategyAngle(BaseModel):
    summary: str
    primary_citations: list[str] = Field(default_factory=list)
    supporting_brief_refs: list[str] = Field(default_factory=list)


class PreemptiveDefense(BaseModel):
    anticipated_counter: str
    rebuttal: str
    citations: list[str] = Field(default_factory=list)


class LetterOutlineItem(BaseModel):
    section: str
    content_hint: str = ""


class EvidenceChecklistItem(BaseModel):
    item: str
    status: Literal["attached", "to_be_attached", "requested_from_insurer"] = (
        "to_be_attached"
    )
    why_it_matters: str = ""


class ProceduralDemand(BaseModel):
    demand: str
    authority: str = ""


class ToneParameters(BaseModel):
    tone_register: str = "formal_calm"
    max_paragraphs: int = 8
    max_words: int = 1200
    no_exclamation_marks: bool = True
    no_emotional_escalation: bool = True


StrategyArchetype = Literal[
    "parity_led",
    "plan_contradicts_itself",
    "clinical_evidence_led",
    "procedural_default",
    "nsa_protected",
    "precedent_bolstered",
]


class AppealStrategy(BaseModel):
    case_id: str
    agent: Literal["strategist"] = "strategist"
    archetype: StrategyArchetype = "clinical_evidence_led"
    lead_angle: StrategyAngle
    supporting_angles: list[StrategyAngle] = Field(default_factory=list)
    preemptive_defenses: list[PreemptiveDefense] = Field(default_factory=list)
    letter_outline: list[LetterOutlineItem] = Field(default_factory=list)
    evidence_checklist_for_drafter: list[EvidenceChecklistItem] = Field(
        default_factory=list
    )
    procedural_demands: list[ProceduralDemand] = Field(default_factory=list)
    tone_parameters: ToneParameters = Field(default_factory=ToneParameters)
    evidence_gaps: list[str] = Field(default_factory=list)
    degraded_strategy: bool = False
    playbook_version_used: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    thinking: str = ""

    def all_citations(self) -> list[str]:
        cites = list(self.lead_angle.primary_citations)
        for angle in self.supporting_angles:
            cites.extend(angle.primary_citations)
        for d in self.preemptive_defenses:
            cites.extend(d.citations)
        return list(dict.fromkeys(cites))


# --- Adversarial review ------------------------------------------------------


class CritiqueFinding(BaseModel):
    issue: str
    severity: float = 0.0  # 0.0-1.0
    fix: str = ""
    category: str = ""


class AdversarialCritique(BaseModel):
    case_id: str
    agent: Literal["adversarial_reviewer"] = "adversarial_reviewer"
    iteration: Literal[1, 2] = 1
    findings: list[CritiqueFinding] = Field(default_factory=list)
    overall_severity: float = 0.0
    passes: bool = True
    resolved_findings: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    thinking: str = ""


# --- Per-agent trace signal (firewall-safe; FR-5 credit assignment) ----------


class AgentTraceSignal(BaseModel):
    """A firewall-safe, per-agent signal emitted once per run (FR-5).

    This is the credit-assignment unit the Learning Coordinator reads to attribute
    a weak quality dimension to the responsible agent. It carries ONLY laundered,
    structural fields - ``role`` + ``prompt_version`` + counts/flags + a templated
    ``summary`` - and NEVER raw letter text, brief quotes, agent ``thinking``, PHI,
    or answer-key provenance (mirrors the Part A anti-cheating firewall, INV-2).
    """

    role: str
    prompt_version: str
    is_weak_v1: bool = False
    owned_dimensions: list[str] = Field(default_factory=list)
    status: str = ""
    finding_count: int = 0
    citation_count: int = 0
    risk_flags: list[str] = Field(default_factory=list)
    summary: str = ""


# --- Run artifacts (sidecar to the terminal AppealPackage) -------------------


class SwarmRunArtifacts(BaseModel):
    """Swarm-internal intermediate outputs, attached alongside the terminal
    ``AppealPackage``. Surfaced for trace richness, the showcase UI, and
    per-agent credit assignment."""

    routing_manifest: RoutingManifest
    briefs: list[ResearchBrief] = Field(default_factory=list)
    insurer_brief: InsurerBrief | None = None
    strategy: AppealStrategy | None = None
    critiques: list[AdversarialCritique] = Field(default_factory=list)
    drafter_iterations: int = 1
    agent_versions: dict[str, str] = Field(default_factory=dict)
    agent_trace_signals: list[AgentTraceSignal] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
