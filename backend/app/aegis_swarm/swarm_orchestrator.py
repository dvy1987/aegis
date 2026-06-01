"""Swarm orchestration layer: Student pipeline + Outcome Simulator.

Mirrors ``aegis_v1/appeal_orchestrator.py``. The simulator is run HERE, wrapping
the Student, never as a Student tool - so the swarm cannot optimize toward
pleasing its own outcome (separation of powers, D11). The eval/grading panel is
deliberately NOT run here (judges need the teacher answer key, which a real
user-submitted appeal does not have); grading lives in the eval layer (Phase 5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.aegis_swarm.corpus_store import CorpusStore
from app.aegis_swarm.swarm_pipeline import RunMode, run_swarm_pipeline

if TYPE_CHECKING:
    from app.aegis_swarm.client import SwarmAgentClient
    from app.aegis_v1.simulator_client import SimulatorClient


class SwarmAppealRunResult(BaseModel):
    """One swarm appeal run: the terminal AppealPackage, the insurer outcome, and
    the swarm-internal artifacts (manifest, briefs, strategy, critiques)."""

    appeal_package: dict[str, Any]
    outcome: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)


def run_swarm_appeal_with_outcome(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    dataset_split: str = "interactive",
    run_mode: RunMode = "interactive",
    client: "SwarmAgentClient | None" = None,
    simulator_client: "SimulatorClient | None" = None,
    corpus_store: CorpusStore | None = None,
    discovery=None,
    trace_recorder=None,
) -> SwarmAppealRunResult:
    """Run the swarm Student, then the Outcome Simulator, and return both + the
    swarm artifacts. Reuses Part A's ``simulator`` so the swarm and Part A share
    one insurer-persona contract."""
    from app.aegis_v1.tools import simulator

    result = run_swarm_pipeline(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
        dataset_split=dataset_split,
        run_mode=run_mode,
        client=client,
        corpus_store=corpus_store,
        discovery=discovery,
        trace_recorder=trace_recorder,
    )
    package = result["appeal_package"]
    outcome = simulator(
        parsed_case=package["parsed_case"],
        appeal_draft=package["appeal_package_draft"],
        self_check_result=package["self_check"],
        client=simulator_client,
    )
    return SwarmAppealRunResult(
        appeal_package=package,
        outcome=outcome,
        artifacts=result["artifacts"],
    )
