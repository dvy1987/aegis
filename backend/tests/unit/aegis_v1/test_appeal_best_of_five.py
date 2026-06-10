"""Phase 2: simulator ADK agent + best-of-two appeal gatekeeper."""

from __future__ import annotations

from app.aegis_v1.appeal_orchestrator import MAX_APPEAL_ATTEMPTS, run_appeal_with_outcome
from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment


DENIAL = (
    "Cigna denied IOP because medical necessity was not shown. Appeal within 180 days."
)
CLINICAL = "Severe OCD requiring IOP."


def test_appeal_best_of_two_returns_first_approve() -> None:
    """D14: return first APPROVE among up to two drafts."""
    calls = {"n": 0}

    class SequenceSimulator:
        name = "seq_sim"

        def assess(self, denial_text, appeal_letter, **kwargs):
            calls["n"] += 1
            anchor = 5 if calls["n"] >= 2 else 1
            return uniform_assessment(anchor, critique=f"attempt {calls['n']}")

    result = run_appeal_with_outcome(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="best_of_2",
        drafter_client=StubDrafterClient(),
        simulator_client=SequenceSimulator(),
    )
    assert MAX_APPEAL_ATTEMPTS == 2
    assert result.outcome["verdict"] == "APPROVE"
    assert calls["n"] == 2


def test_max_attempts_one_does_not_retry_after_deny() -> None:
    calls = {"n": 0}

    class AlwaysDenySimulator:
        name = "always_deny"

        def assess(self, denial_text, appeal_letter, **kwargs):
            calls["n"] += 1
            return uniform_assessment(1, critique=f"attempt {calls['n']}")

    result = run_appeal_with_outcome(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="single_attempt",
        drafter_client=StubDrafterClient(),
        simulator_client=AlwaysDenySimulator(),
        max_attempts=1,
    )

    assert result.outcome["verdict"] == "DENY"
    assert calls["n"] == 1


def test_appeal_best_of_two_all_deny_returns_highest_score() -> None:
    """D14: if both DENY, return highest simulator score."""
    scores = [0.2, 0.38]
    idx = {"i": 0}

    class ScoredSimulator:
        name = "scored_sim"

        def assess(self, denial_text, appeal_letter, **kwargs):
            i = idx["i"]
            idx["i"] += 1
            anchor = {0.2: 1, 0.38: 1}[scores[min(i, 1)]]
            return uniform_assessment(anchor, critique=f"score target {scores[min(i, 1)]}")

    result = run_appeal_with_outcome(
        denial_text=DENIAL,
        clinical_context=CLINICAL,
        case_id="best_deny",
        drafter_client=StubDrafterClient(),
        simulator_client=ScoredSimulator(),
    )
    assert result.outcome["verdict"] == "DENY"
    assert idx["i"] == 2
