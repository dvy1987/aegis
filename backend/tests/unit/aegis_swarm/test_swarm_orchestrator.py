from __future__ import annotations

from app.aegis_swarm.client import StubSwarmClient
from app.aegis_swarm.corpus_store import LocalCorpusStore
from app.aegis_swarm.swarm_orchestrator import (
    SwarmAppealRunResult,
    run_swarm_appeal_with_outcome,
)
from app.aegis_v1.simulator_client import StubSimulatorClient

_DENIAL = (
    "UnitedHealthcare denied continued SNF coverage as not medically necessary. "
    "Per nH Predict the member reached maximum expected function. Appeal within 60 days."
)


def test_orchestrator_runs_student_then_simulator_offline() -> None:
    result = run_swarm_appeal_with_outcome(
        denial_text=_DENIAL,
        clinical_context="Documented ongoing rehab needs.",
        case_id="syn-uhc-snf-007",
        client=StubSwarmClient(),
        simulator_client=StubSimulatorClient(),
        corpus_store=LocalCorpusStore(),
    )
    assert isinstance(result, SwarmAppealRunResult)
    assert result.outcome["verdict"] in {"APPROVE", "DENY"}
    assert result.appeal_package["appeal_package_draft"]["appeal_letter"]
    assert result.artifacts["routing_manifest"]["case_id"] == "syn-uhc-snf-007"


def test_orchestrator_outcome_has_score_and_threshold() -> None:
    result = run_swarm_appeal_with_outcome(
        denial_text=_DENIAL,
        client=StubSwarmClient(),
        simulator_client=StubSimulatorClient(),
        corpus_store=LocalCorpusStore(),
    )
    assert 0.0 <= result.outcome["score"] <= 1.0
    assert "threshold" in result.outcome
