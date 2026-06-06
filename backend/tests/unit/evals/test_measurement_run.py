from __future__ import annotations

import pytest

from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
from app.evals.part_a.measurement_run import run_measurement_case


CASE = {
    "case_id": "measurement_case",
    "denial_letter_text": "Cigna denied coverage for infusion therapy because it was not medically necessary.",
    "clinical_context": "The person has severe symptoms despite conservative care.",
}


def test_measurement_runner_returns_simulator_outcome() -> None:
    result = run_measurement_case(
        CASE,
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(uniform_assessment(5)),
    )

    assert result.case_id == "measurement_case"
    assert result.verdict == "APPROVE"
    assert result.score == 1.0
    assert result.letter_excerpt


def test_measurement_runner_does_not_read_phoenix_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_lookup(*args, **kwargs):
        raise AssertionError("measurement must not read Phoenix memory")

    monkeypatch.setattr("app.aegis_v1.pipeline.phoenix_mcp_lookup", fail_lookup)

    result = run_measurement_case(
        CASE,
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(uniform_assessment(3)),
    )

    assert result.case_id == "measurement_case"
