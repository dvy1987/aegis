from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from app.aegis_v1.drafter_client import DrafterLLMClient
from app.aegis_v1.phoenix_mode import PhoenixMode
from app.aegis_v1.pipeline import run_aegis_v1_pipeline

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

    package = run_aegis_v1_pipeline(
        denial_text=case_obj.get("denial_letter_text", ""),
        clinical_context=case_obj.get("clinical_context", ""),
        case_id=case_obj.get("case_id", "interactive_case"),
        dataset_split=case_obj.get("dataset_split", "showcase_measure"),
        run_mode="benchmark",
        phoenix_mode=PhoenixMode.HOLDOUT_READONLY,
        drafter_client=drafter_client,
        drafter_prompt_version=drafter_prompt_version,
        drafter_prompt_text=drafter_prompt_text,
        playbook_override=playbook_override,
    )

    from app.aegis_v1.tools import simulator

    sim = simulator(
        parsed_case=package["parsed_case"],
        appeal_draft=package["appeal_package_draft"],
        self_check_result=package["self_check"],
        client=simulator_client,
    )
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
