from app.aegis_v1.appeal_orchestrator import AppealRunResult, run_appeal_with_outcome
from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient

CIGNA_DENIAL = (
    "We reviewed the request for TMS for treatment-resistant depression. "
    "Cigna denied the request as not medically necessary. You may appeal within 180 days."
)


def test_orchestrator_surfaces_letter_and_outcome_offline():
    result = run_appeal_with_outcome(
        denial_text=CIGNA_DENIAL,
        clinical_context="Patient failed two SSRIs; severe treatment-resistant depression.",
        case_id="case_demo",
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(verdict="APPROVE", score=10),
    )
    assert isinstance(result, AppealRunResult)
    # the appeal letter is present (Student output)
    assert result.appeal_package["appeal_package_draft"]["appeal_letter"]
    # the per-appeal outcome is present and carries the injected verdict (the fixed seam)
    assert result.outcome["verdict"] == "APPROVE"
    assert result.outcome["score"] == 10
    # separation of powers: the Student package itself does NOT carry the outcome
    assert "simulator_result" not in result.appeal_package


def test_orchestrator_outcome_reflects_a_deny():
    result = run_appeal_with_outcome(
        denial_text=CIGNA_DENIAL,
        clinical_context="Sparse notes.",
        case_id="case_deny",
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(verdict="DENY", score=3),
    )
    assert result.outcome["verdict"] == "DENY"
    assert result.appeal_package["trace_metadata"]["case_id"] == "case_deny"
