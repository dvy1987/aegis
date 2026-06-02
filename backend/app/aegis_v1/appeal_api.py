from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import BaseModel

from app.aegis_v1.appeal_orchestrator import run_appeal_with_outcome
from app.aegis_v1.v1_config import build_v1_library_stack

router = APIRouter(prefix="/v1", tags=["appeal"])


class AppealRequest(BaseModel):
    denial_text: str
    clinical_context: str = ""
    case_id: str = "interactive_case"
    discovery_enabled: bool = False


class AppealResponse(BaseModel):
    run_id: str
    appeal_letter: str
    outcome: dict[str, Any]
    risk_flags: list[str]
    trace_metadata: dict[str, Any]


def get_drafter_client():
    """Production drafter (Vertex/Gemini). Overridden with a stub in tests."""
    from app.aegis_v1.drafter_client import GeminiDrafterClient

    return GeminiDrafterClient()


def get_simulator_client():
    """Production Outcome Simulator (Vertex/Gemini). Overridden with a stub in tests."""
    from app.aegis_v1.simulator_client import GeminiSimulatorClient

    return GeminiSimulatorClient()


@router.post("/appeal", response_model=AppealResponse)
def create_appeal(
    req: AppealRequest,
    drafter_client=Depends(get_drafter_client),
    simulator_client=Depends(get_simulator_client),
) -> AppealResponse:
    """Draft an appeal and return it together with the insurer Outcome Simulator
    verdict — the artifact the UX shows per appeal run."""
    library_stack = build_v1_library_stack(discovery_enabled=req.discovery_enabled)
    if req.discovery_enabled and not library_stack.get("uses_vertex_store"):
        raise HTTPException(
            status_code=503,
            detail=(
                "Discovery requested but the cloud library is unavailable. "
                "Configure Vertex AI Search (VERTEX_SEARCH_* env vars + credentials) "
                "and try again, or rerun with discovery_enabled=false."
            ),
        )
    result = run_appeal_with_outcome(
        denial_text=req.denial_text,
        clinical_context=req.clinical_context,
        case_id=req.case_id,
        drafter_client=drafter_client,
        simulator_client=simulator_client,
        library_stack=library_stack,
    )
    pkg = result.appeal_package
    return AppealResponse(
        run_id=pkg["run_id"],
        appeal_letter=pkg["appeal_package_draft"]["appeal_letter"],
        outcome=result.outcome,
        risk_flags=pkg["risk_flags"],
        trace_metadata=pkg["trace_metadata"],
    )
