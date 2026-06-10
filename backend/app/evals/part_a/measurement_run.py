from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from app.aegis_v1.appeal_orchestrator import (
    SHOWCASE_MEASUREMENT_MAX_ATTEMPTS,
    run_appeal_with_outcome,
)
from app.aegis_v1.drafter_client import DrafterLLMClient
from app.aegis_v1.phoenix_mode import PhoenixMode

if TYPE_CHECKING:
    from app.aegis_v1.simulator_client import SimulatorClient


class MeasurementResult(BaseModel):
    case_id: str
    verdict: Literal["APPROVE", "DENY"]
    score: float
    threshold: float
    letter_excerpt: str
    prompt_version: str
    risk_flags: list[str]


def _excerpt(text: str, limit: int = 520) -> str:
    compact = " ".join((text or "").split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def run_measurement_case(
    case_obj: dict[str, Any],
    *,
    drafter_client: DrafterLLMClient | None = None,
    simulator_client: "SimulatorClient | None" = None,
    drafter_prompt_version: str | None = None,
    drafter_prompt_text: str | None = None,
    playbook_override: dict[str, Any] | None = None,
) -> MeasurementResult:
    """Run clean measurement: v1 drafter plus simulator only.

    This path deliberately bypasses `run_evaluated_case`: no recorder, no judges,
    no Phoenix annotations, and no LearningCoordinator signal. The drafter still
    receives the same sanitized Phoenix memory summary used by normal v1 drafting.
    """

    from app.aegis_v1.patient_context import pipeline_inputs_from_case

    appeal = run_appeal_with_outcome(
        **pipeline_inputs_from_case(case_obj),
        dataset_split=case_obj.get("dataset_split", "showcase_measure"),
        run_mode="benchmark",
        phoenix_mode=PhoenixMode.HOLDOUT_READONLY,
        drafter_client=drafter_client,
        simulator_client=simulator_client,
        max_attempts=SHOWCASE_MEASUREMENT_MAX_ATTEMPTS,
        drafter_prompt_version=drafter_prompt_version,
        drafter_prompt_text=drafter_prompt_text,
        playbook_override=playbook_override,
    )
    package = appeal.appeal_package
    sim = appeal.outcome
    draft = package["appeal_package_draft"]
    metadata = package["trace_metadata"]
    return MeasurementResult(
        case_id=package["parsed_case"]["case_id"],
        verdict=sim["verdict"],
        score=float(sim["score"]),
        threshold=float(sim["threshold"]),
        letter_excerpt=_excerpt(draft.get("appeal_letter", "")),
        prompt_version=str(metadata.get("prompt_version") or drafter_prompt_version or ""),
        risk_flags=list(package.get("risk_flags") or []),
    )
