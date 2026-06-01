from __future__ import annotations

from app.aegis_swarm.schemas import (
    AdversarialCritique,
    AppealStrategy,
    BriefCitation,
    CritiqueFinding,
    InsurerBrief,
    ResearchBrief,
    ResearchFinding,
    ResearcherInvocation,
    RoutingManifest,
    StrategyAngle,
    SwarmRunArtifacts,
)


def _manifest() -> RoutingManifest:
    return RoutingManifest(
        case_id="syn-1",
        denial_type="medical_necessity",
        confidence=0.9,
        complexity_score=3,
        researchers=[
            ResearcherInvocation(name="insurer_intelligence", invoke=True),
            ResearcherInvocation(name="precedent_miner", invoke=False),
            ResearcherInvocation(name="medical_necessity", invoke=True),
        ],
    )


def test_routing_manifest_invoked_filters_to_invoke_true() -> None:
    assert _manifest().invoked() == ["insurer_intelligence", "medical_necessity"]


def test_research_brief_flattens_citations() -> None:
    brief = ResearchBrief(
        agent="legal_researcher",
        case_id="syn-1",
        domain="legal",
        findings=[
            ResearchFinding(
                summary="ERISA full and fair review",
                citations=[BriefCitation(corpus_doc_id="erisa_503.md")],
            ),
            ResearchFinding(
                summary="parity",
                citations=[BriefCitation(corpus_doc_id="mhpaea_parity.md")],
            ),
        ],
    )
    assert [c.corpus_doc_id for c in brief.all_citations()] == [
        "erisa_503.md",
        "mhpaea_parity.md",
    ]


def test_insurer_brief_defaults_and_unavailable_shape() -> None:
    empty = InsurerBrief(case_id="syn-1", status="empty", tactic="",
                         risk_flags=["phoenix_mcp_unavailable"])
    assert empty.agent == "insurer_intelligence"
    assert empty.domain == "insurer"
    assert empty.tactic == ""
    assert "phoenix_mcp_unavailable" in empty.risk_flags


def test_appeal_strategy_dedupes_citations_across_angles() -> None:
    strategy = AppealStrategy(
        case_id="syn-1",
        lead_angle=StrategyAngle(
            summary="lead", primary_citations=["29 CFR 2560.503-1", "erisa_503.md"]
        ),
        supporting_angles=[
            StrategyAngle(summary="support", primary_citations=["erisa_503.md"])
        ],
    )
    assert strategy.all_citations() == ["29 CFR 2560.503-1", "erisa_503.md"]


def test_swarm_run_artifacts_round_trip() -> None:
    artifacts = SwarmRunArtifacts(
        routing_manifest=_manifest(),
        briefs=[ResearchBrief(agent="medical_necessity", case_id="syn-1", domain="clinical")],
        insurer_brief=InsurerBrief(case_id="syn-1"),
        critiques=[
            AdversarialCritique(
                case_id="syn-1",
                findings=[CritiqueFinding(issue="weak lead", severity=0.5)],
                passes=False,
            )
        ],
        agent_versions={"drafter": "v1"},
    )
    restored = SwarmRunArtifacts.model_validate(artifacts.model_dump())
    assert restored.routing_manifest.case_id == "syn-1"
    assert restored.critiques[0].passes is False
    assert restored.agent_versions["drafter"] == "v1"
