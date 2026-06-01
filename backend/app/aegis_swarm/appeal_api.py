"""HTTP API for the swarm appeal pipeline (mirrors Part A ``appeal_api``)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.aegis_swarm.swarm_config import build_live_stack
from app.aegis_swarm.swarm_orchestrator import run_swarm_appeal_with_outcome
from app.aegis_swarm.trace_recorder import build_trace_recorder

router = APIRouter(prefix="/v1", tags=["swarm"])


def get_swarm_stack():
    return build_live_stack()


def get_trace_recorder():
    return build_trace_recorder()


def get_simulator_client():
    from app.aegis_v1.simulator_client import GeminiSimulatorClient

    return GeminiSimulatorClient()


class SwarmAppealRequest(BaseModel):
    denial_text: str
    clinical_context: str = ""
    case_id: str = "interactive_case"


class SwarmAppealResponse(BaseModel):
    run_id: str
    appeal_letter: str
    outcome: dict[str, Any]
    risk_flags: list[str]
    trace_metadata: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)


@router.post("/swarm/appeal", response_model=SwarmAppealResponse)
def create_swarm_appeal(
    req: SwarmAppealRequest,
    stack=Depends(get_swarm_stack),
    trace_recorder=Depends(get_trace_recorder),
    simulator_client=Depends(get_simulator_client),
) -> SwarmAppealResponse:
    """Draft an appeal via the swarm and return the Outcome Simulator verdict."""
    result = run_swarm_appeal_with_outcome(
        denial_text=req.denial_text,
        clinical_context=req.clinical_context,
        case_id=req.case_id,
        client=stack["client"],
        corpus_store=stack["corpus_store"],
        discovery=stack["discovery"],
        trace_recorder=trace_recorder,
        simulator_client=simulator_client,
    )
    pkg = result.appeal_package
    return SwarmAppealResponse(
        run_id=pkg["run_id"],
        appeal_letter=pkg["appeal_package_draft"]["appeal_letter"],
        outcome=result.outcome,
        risk_flags=pkg["risk_flags"],
        trace_metadata=pkg["trace_metadata"],
        artifacts=result.artifacts,
    )
