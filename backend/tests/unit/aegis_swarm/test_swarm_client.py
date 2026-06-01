from __future__ import annotations

from app.aegis_swarm.client import (
    GeminiSwarmClient,
    StubSwarmClient,
    SwarmAgentClient,
)
from app.aegis_swarm.corpus_store import CorpusHit
from app.aegis_swarm.schemas import (
    AppealStrategy,
    InsurerBrief,
    ResearchBrief,
    RoutingManifest,
    StrategyAngle,
)

_PARSED = {
    "case_id": "syn-001",
    "insurer": "Cigna",
    "denial_type": "medical_necessity",
    "service_or_procedure": "esketamine",
    "diagnosis_summary": "treatment-resistant depression",
    "cited_denial_reason": "conservative therapy not exhausted",
    "missing_facts": [],
}

_HITS = [
    CorpusHit(
        corpus_doc_id="clinical_a.md",
        title="Clinical Evidence A",
        quote="documented two failed trials",
        relevance_score=1.2,
        domain="clinical",
    )
]


def test_stub_satisfies_protocol() -> None:
    assert isinstance(StubSwarmClient(), SwarmAgentClient)


def test_stub_triage_invokes_a_researcher() -> None:
    manifest = StubSwarmClient().triage(_PARSED)
    assert isinstance(manifest, RoutingManifest)
    assert manifest.denial_type == "medical_necessity"
    assert "medical_necessity" in manifest.invoked()


def test_stub_triage_always_invokes_insurer_intelligence() -> None:
    # Phoenix-MCP load-bearing: insurer_intelligence is never skipped.
    for denial in ("medical_necessity", "prior_authorization", "coverage_exclusion"):
        manifest = StubSwarmClient().triage({**_PARSED, "denial_type": denial})
        assert "insurer_intelligence" in manifest.invoked()


def test_stub_triage_fans_out_per_routing_table() -> None:
    manifest = StubSwarmClient().triage(_PARSED)
    invoked = set(manifest.invoked())
    # medical_necessity -> medical_necessity + policy_detective + insurer_intelligence.
    assert {"medical_necessity", "policy_detective", "insurer_intelligence"} <= invoked


def test_stub_triage_complexity_5_adds_precedent_miner() -> None:
    parsed = {**_PARSED, "state": "CA"}
    manifest = StubSwarmClient().triage(parsed)
    assert manifest.complexity_score == 5
    assert "precedent_miner" in manifest.invoked()
    assert all(r.depth == "deep" for r in manifest.researchers)


def test_stub_triage_maps_prior_auth_denial_type() -> None:
    parsed = {**_PARSED, "denial_type": "prior_authorization"}
    assert StubSwarmClient().triage(parsed).denial_type == "prior_auth_missing"


def test_stub_research_wraps_hits_into_findings() -> None:
    brief = StubSwarmClient().research("medical_necessity", _PARSED, "standard", _HITS)
    assert isinstance(brief, ResearchBrief)
    assert brief.domain == "clinical"
    assert brief.status == "full"
    assert brief.all_citations()[0].corpus_doc_id == "clinical_a.md"


def test_stub_research_empty_hits_flags_gap() -> None:
    brief = StubSwarmClient().research("medical_necessity", _PARSED, "brief", [])
    assert brief.status == "empty"
    assert "no_guidelines_found" in brief.risk_flags


def test_stub_research_per_domain_empty_flags() -> None:
    # Each researcher reports its own "nothing found" signal; precedent "no match"
    # must NOT masquerade as a guidelines/statute gap.
    cases = {
        "legal_researcher": "no_statute_found",
        "policy_detective": "cpb_not_found",
        "precedent_miner": "no_precedent_found",
    }
    for agent, expected in cases.items():
        brief = StubSwarmClient().research(agent, _PARSED, "brief", [])
        assert expected in brief.risk_flags
        assert "no_guidelines_found" not in brief.risk_flags


def test_stub_research_legal_flags_state_unknown() -> None:
    parsed = {**_PARSED, "state": "unknown"}
    brief = StubSwarmClient().research("legal_researcher", parsed, "standard", _HITS)
    assert "state_unknown" in brief.risk_flags
    assert brief.evidence_gaps  # always-include procedural angle


def test_stub_research_policy_flags_missing_plan_docs() -> None:
    parsed = {**_PARSED, "missing_facts": ["plan_document_language"]}
    brief = StubSwarmClient().research("policy_detective", parsed, "standard", _HITS)
    assert "missing_plan_docs" in brief.risk_flags


def test_stub_research_insurer_returns_insurer_brief_with_mcp_flag() -> None:
    brief = StubSwarmClient().research(
        "insurer_intelligence",
        _PARSED,
        "standard",
        _HITS,
        phoenix_summary={"status": "disabled", "risk_flags": ["phoenix_mcp_disabled"]},
    )
    assert isinstance(brief, InsurerBrief)
    assert "phoenix_mcp_unavailable" in brief.risk_flags
    assert brief.tactic == ""


def test_stub_strategize_only_uses_brief_citations() -> None:
    briefs = [StubSwarmClient().research("medical_necessity", _PARSED, "standard", _HITS)]
    strategy = StubSwarmClient().strategize(_PARSED, briefs, StubSwarmClient().triage(_PARSED), {"version": "v3"})
    assert isinstance(strategy, AppealStrategy)
    assert "clinical_a.md" in strategy.lead_angle.primary_citations
    assert strategy.playbook_version_used == "v3"
    assert strategy.degraded_strategy is False


def test_stub_draft_includes_disclaimer() -> None:
    strategy = AppealStrategy(
        case_id="syn-001",
        lead_angle=StrategyAngle(summary="lead"),
    )
    letter = StubSwarmClient().draft(_PARSED, strategy, _HITS, {}, {})
    assert "not legal or medical advice" in letter.lower()
    assert "Cigna" in letter


def test_stub_critique_passes_when_disclaimer_present() -> None:
    strategy = AppealStrategy(case_id="syn-001", lead_angle=StrategyAngle(summary="lead"))
    letter = StubSwarmClient().draft(_PARSED, strategy, _HITS, {}, {})
    critique = StubSwarmClient().critique(_PARSED, strategy, letter)
    assert critique.passes is True
    assert critique.overall_severity < 0.6


def test_stub_critique_flags_missing_disclaimer() -> None:
    strategy = AppealStrategy(case_id="syn-001", lead_angle=StrategyAngle(summary="lead"))
    critique = StubSwarmClient().critique(_PARSED, strategy, "letter with no disclaimer")
    assert critique.passes is False
    assert critique.overall_severity >= 0.6


def test_gemini_client_constructs_offline() -> None:
    client = GeminiSwarmClient(model="gemini-test", location="us-central1")
    assert client.name == "gemini_swarm"
    assert client.model == "gemini-test"
    assert isinstance(client, SwarmAgentClient)
