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


class CapturingDrafterClient:
    name = "capturing"

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.playbooks: list[dict] = []

    def draft(self, prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
        self.prompts.append(prompt)
        self.playbooks.append(playbook)
        return StubDrafterClient().draft(prompt, parsed_case, citations, playbook, phoenix_summary)


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


def test_measurement_runner_can_use_candidate_prompt_text_without_promotion() -> None:
    drafter = CapturingDrafterClient()

    result = run_measurement_case(
        CASE,
        drafter_client=drafter,
        simulator_client=StubSimulatorClient(uniform_assessment(3)),
        drafter_prompt_version="candidate_v3",
        drafter_prompt_text="candidate prompt text",
    )

    assert drafter.prompts == ["candidate prompt text"]
    assert result.prompt_version == "candidate_v3"


def test_measurement_runner_can_use_candidate_playbook_without_promotion() -> None:
    drafter = CapturingDrafterClient()

    result = run_measurement_case(
        CASE,
        drafter_client=drafter,
        simulator_client=StubSimulatorClient(uniform_assessment(3)),
        playbook_override={
            "insurer": "Cigna",
            "denial_type": "medical_necessity",
            "version": "candidate_playbook_v3",
            "tactics": ["Use the candidate tactic."],
            "required_evidence": [],
            "risk_flags": [],
        },
    )

    assert drafter.playbooks[0]["version"] == "candidate_playbook_v3"
    assert drafter.playbooks[0]["tactics"] == ["Use the candidate tactic."]
    assert result.case_id == "measurement_case"
