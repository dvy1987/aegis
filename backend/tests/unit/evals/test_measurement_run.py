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
        self.phoenix_summaries: list[dict] = []

    def draft(self, prompt, parsed_case, citations, playbook, phoenix_summary) -> str:
        self.prompts.append(prompt)
        self.playbooks.append(playbook)
        self.phoenix_summaries.append(phoenix_summary)
        return StubDrafterClient().draft(prompt, parsed_case, citations, playbook, phoenix_summary)


def test_holdout_measure_does_not_write_phoenix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan §17.4: holdout measure must never call record_run."""
    calls: list[str] = []

    def _blocked_record(self, appeal_package, trace_metadata) -> str:
        calls.append("record_run")
        return "blocked"

    monkeypatch.setattr(
        "app.evals.part_a.recorder.OtelPhoenixRecorder.record_run",
        _blocked_record,
    )

    def _blocked_export(*args, **kwargs):
        calls.append("write_appeal_phoenix_export")
        return None

    monkeypatch.setattr(
        "app.aegis_v1.appeal_phoenix_export.write_appeal_phoenix_export",
        _blocked_export,
    )

    run_measurement_case(
        CASE,
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(uniform_assessment(5)),
    )
    assert calls == []


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


def test_measurement_runner_reads_sanitized_phoenix_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phoenix memory is read before drafting and reflected in risk flags."""

    def fake_lookup(*args, **kwargs):
        return {
            "status": "available",
            "query": "fake",
            "similar_trace_count": 1,
            "failure_patterns": ["Address the specific denial flaw."],
            "success_traits": ["strong appeal_vector_capture"],
            "risk_flags": ["phoenix_mcp_live"],
        }

    # Patch where the @node function imports it (student_workflow → tools)
    monkeypatch.setattr("app.aegis_v1.tools.phoenix_mcp_lookup", fake_lookup)

    result = run_measurement_case(
        CASE,
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(uniform_assessment(3)),
    )

    assert result.case_id == "measurement_case"
    # Phoenix risk flag should propagate to the output
    assert "phoenix_mcp_live" in result.risk_flags


def test_measurement_runner_can_use_candidate_prompt_text_without_promotion() -> None:
    result = run_measurement_case(
        CASE,
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(uniform_assessment(3)),
        drafter_prompt_version="candidate_v3",
        drafter_prompt_text="candidate prompt text",
    )

    # Prompt version is carried through the ADK workflow state → trace metadata
    assert result.prompt_version == "candidate_v3"


def test_measurement_runner_can_use_candidate_playbook_without_promotion() -> None:
    result = run_measurement_case(
        CASE,
        drafter_client=StubDrafterClient(),
        simulator_client=StubSimulatorClient(uniform_assessment(3)),
        playbook_override={
            "insurer": "Cigna",
            "denial_type": "medical_necessity",
            "version": "candidate_playbook_v3",
            "status": "loaded",
            "tactics": ["Use the candidate tactic."],
            "required_evidence": [],
            "risk_flags": [],
        },
    )

    assert result.case_id == "measurement_case"
