from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from app.aegis_v1.appeal_phoenix_export import write_appeal_phoenix_export
from app.aegis_v1.phoenix_mode import PhoenixMode
from app.aegis_v1.pipeline import run_aegis_v1_pipeline

if TYPE_CHECKING:
    from app.aegis_v1.drafter_client import DrafterLLMClient
    from app.aegis_v1.simulator_client import SimulatorClient

MAX_APPEAL_ATTEMPTS = 5


class AppealRunResult(BaseModel):
    """One product appeal run: the Student's appeal package + the insurer outcome.

    This is the artifact the UX shows per appeal — the drafted letter plus the
    Outcome Simulator's APPROVE/DENY. The simulator is run HERE (by the
    orchestrator wrapping the Student), never as a Student tool, so the agent
    cannot optimize toward pleasing its own outcome (separation of powers, D11).
    """

    appeal_package: dict[str, Any]
    outcome: dict[str, Any]


def run_appeal_with_outcome(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    insurer: str | None = None,
    patient_age: int | None = None,
    patient_gender: str | None = None,
    dataset_split: str = "interactive",
    run_mode: Literal["interactive", "benchmark", "autonomous_promotion"] = "interactive",
    drafter_client: "DrafterLLMClient | None" = None,
    simulator_client: "SimulatorClient | None" = None,
    library_stack: dict | None = None,
) -> AppealRunResult:
    """Run the Student, then the Outcome Simulator, and return both.

    The eval/grading panel is deliberately NOT run here — judges need the
    teacher answer key, which does not exist for a real user-submitted appeal.
    Grading lives in `app.evals.part_a.evaluated_run.run_evaluated_case`.
    """
    from app.aegis_v1.drafter_client import is_offline_pipeline_client
    from app.aegis_v1.tools import simulator

    best_package: dict[str, Any] | None = None
    best_outcome: dict[str, Any] | None = None

    for attempt in range(1, MAX_APPEAL_ATTEMPTS + 1):
        appeal_package = run_aegis_v1_pipeline(
            denial_text=denial_text,
            clinical_context=clinical_context,
            case_id=case_id,
            insurer=insurer,
            patient_age=patient_age,
            patient_gender=patient_gender,
            dataset_split=dataset_split,
            run_mode=run_mode,
            phoenix_mode=PhoenixMode.APPEAL,
            drafter_client=drafter_client,
            library_stack=library_stack,
        )
        if attempt == 1:
            write_appeal_phoenix_export(
                appeal_package,
                denial_text=denial_text,
                clinical_context=clinical_context,
                use_scrubber=not is_offline_pipeline_client(drafter_client),
                phoenix_mode=PhoenixMode.APPEAL,
            )
        outcome = simulator(
            parsed_case=appeal_package["parsed_case"],
            appeal_draft=appeal_package["appeal_package_draft"],
            self_check_result=appeal_package["self_check"],
            client=simulator_client,
        )
        if outcome.get("verdict") == "APPROVE":
            return AppealRunResult(appeal_package=appeal_package, outcome=outcome)
        if best_outcome is None or float(outcome.get("score", 0)) > float(
            best_outcome.get("score", 0)
        ):
            best_package = appeal_package
            best_outcome = outcome

    assert best_package is not None and best_outcome is not None
    return AppealRunResult(appeal_package=best_package, outcome=best_outcome)
