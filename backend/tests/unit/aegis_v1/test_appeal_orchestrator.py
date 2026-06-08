from app.aegis_v1.appeal_orchestrator import AppealRunResult, run_appeal_with_outcome
from app.aegis_v1.appeal_phoenix_export import in_memory_recorder, write_appeal_phoenix_export
from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment

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
        simulator_client=StubSimulatorClient(assessment=uniform_assessment(5)),
    )
    assert isinstance(result, AppealRunResult)
    # the appeal letter is present (Student output)
    assert result.appeal_package["appeal_package_draft"]["appeal_letter"]
    # the per-appeal outcome is present and carries the injected verdict (the fixed seam)
    assert result.outcome["verdict"] == "APPROVE"
    assert result.outcome["score"] == 1.0
    # separation of powers: the Student package itself does NOT carry the outcome
    assert "simulator_result" not in result.appeal_package


def test_orchestrator_writes_redacted_phoenix_export(monkeypatch) -> None:
    recorder = in_memory_recorder()

    def _record(pkg, **kw):
        return write_appeal_phoenix_export(
            pkg,
            recorder=recorder,
            use_scrubber=False,
            denial_text=kw.get("denial_text", ""),
            clinical_context=kw.get("clinical_context", ""),
        )

    monkeypatch.setattr(
        "app.aegis_v1.appeal_orchestrator.write_appeal_phoenix_export",
        _record,
    )
    run_appeal_with_outcome(
        denial_text=CIGNA_DENIAL,
        clinical_context="Member ID: CIG-98765432. Severe treatment-resistant depression.",
        case_id="phoenix_export",
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(assessment=uniform_assessment(5)),
    )
    assert len(recorder._runs) == 1
    ref = next(iter(recorder._runs))
    stored = recorder._runs[ref]
    letter = stored["appeal_package"]["appeal_package_draft"]["appeal_letter"]
    assert "CIG-98765432" not in letter
    assert stored["metadata"]["phoenix_mode"] == "appeal"
    assert stored["metadata"]["redacted_export"] == "true"


def test_orchestrator_outcome_reflects_a_deny():
    result = run_appeal_with_outcome(
        denial_text=CIGNA_DENIAL,
        clinical_context="Sparse notes.",
        case_id="case_deny",
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(assessment=uniform_assessment(1)),
    )
    assert result.outcome["verdict"] == "DENY"
    assert result.appeal_package["trace_metadata"]["case_id"] == "case_deny"
