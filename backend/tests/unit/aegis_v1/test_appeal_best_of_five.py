"""Phase 2: simulator ADK agent + best-of-5 appeal gatekeeper."""

from __future__ import annotations

from app.aegis_v1.appeal_orchestrator import run_appeal_with_outcome
from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment


DENIAL = (
    "Cigna denied IOP because medical necessity was not shown. Appeal within 180 days."
)
CLINICAL = "Severe OCD requiring IOP."


def test_appeal_best_of_five_returns_first_approve(monkeypatch) -> None:
    """D14: return first APPROVE among up to five drafts."""
    calls = {"n": 0}

    class SequenceSimulator:
        name = "seq_sim"

        def assess(self, denial_text, appeal_letter, **kwargs):
            calls["n"] += 1
            anchor = 5 if calls["n"] >= 3 else 1
            return uniform_assessment(anchor, critique=f"attempt {calls['n']}")

    monkeypatch.setattr(
        "app.aegis_v1.appeal_orchestrator.MAX_APPEAL_ATTEMPTS",
        5,
    )

    result = run_appeal_with_outcome(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="best_of_5",
        drafter_client=StubDrafterClient(),
        simulator_client=SequenceSimulator(),
    )
    assert result.outcome["verdict"] == "APPROVE"
    assert calls["n"] == 3


def test_appeal_best_of_five_all_deny_returns_highest_score(monkeypatch) -> None:
    """D14: if all DENY, return highest simulator score."""
    scores = [0.2, 0.38, 0.55, 0.41, 0.33]
    idx = {"i": 0}

    class ScoredSimulator:
        name = "scored_sim"

        def assess(self, denial_text, appeal_letter, **kwargs):
            i = idx["i"]
            idx["i"] += 1
            anchor = {0.2: 1, 0.38: 1, 0.55: 3, 0.41: 3, 0.33: 1}[scores[min(i, 4)]]
            return uniform_assessment(anchor, critique=f"score target {scores[min(i,4)]}")

    monkeypatch.setattr("app.aegis_v1.appeal_orchestrator.MAX_APPEAL_ATTEMPTS", 5)

    result = run_appeal_with_outcome(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="best_deny",
        drafter_client=StubDrafterClient(),
        simulator_client=ScoredSimulator(),
    )
    assert result.outcome["verdict"] == "DENY"
    assert result.outcome["score"] >= 0.5
