from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from app.aegis_v1.pipeline import run_aegis_v1_pipeline

if TYPE_CHECKING:
    from app.aegis_v1.drafter_client import DrafterLLMClient
    from app.aegis_v1.simulator_client import SimulatorClient


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
    from app.aegis_v1.tools import simulator

    appeal_package = run_aegis_v1_pipeline(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
        dataset_split=dataset_split,
        run_mode=run_mode,
        drafter_client=drafter_client,
        library_stack=library_stack,
    )
    outcome = simulator(
        parsed_case=appeal_package["parsed_case"],
        appeal_draft=appeal_package["appeal_package_draft"],
        self_check_result=appeal_package["self_check"],
        client=simulator_client,
    )
    return AppealRunResult(appeal_package=appeal_package, outcome=outcome)
