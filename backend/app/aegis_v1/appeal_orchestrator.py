from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from app.aegis_v1.appeal_phoenix_export import write_appeal_phoenix_export
from app.aegis_v1.phoenix_mode import PhoenixMode
from app.aegis_v1.pipeline import run_aegis_v1_pipeline

if TYPE_CHECKING:
    from app.aegis_v1.drafter_client import DrafterLLMClient
    from app.aegis_v1.simulator_client import SimulatorClient

MAX_APPEAL_ATTEMPTS = 2
SHOWCASE_MEASUREMENT_MAX_ATTEMPTS = 1


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
    max_attempts: int | None = None,
    phoenix_mode: PhoenixMode = PhoenixMode.APPEAL,
    drafter_prompt_version: str | None = None,
    drafter_prompt_text: str | None = None,
    playbook_override: dict[str, Any] | None = None,
    geo_playbook_override: dict[str, Any] | None = None,
    use_phoenix_memory: bool = True,
    run_question_agent: bool = False,
    question_agent_client: Any | None = None,
    patient_simulator_client: Any | None = None,
    teacher_clinical_context: str = "",
    patient_profile: dict[str, Any] | None = None,
    question_interview: dict[str, Any] | None = None,
) -> AppealRunResult:
    """Run the Student, then the Outcome Simulator, and return both.

    The eval/grading panel is deliberately NOT run here — judges need the
    teacher answer key, which does not exist for a real user-submitted appeal.
    Grading lives in `app.evals.part_a.evaluated_run.run_evaluated_case`.

    The question agent runs as a node INSIDE the Student workflow. On showcase
    measurement (``run_question_agent``) the patient simulator answers from
    ``teacher_clinical_context``, which lives ONLY in the responder closure —
    never in workflow state (firewall INV-QA). On a real appeal, pass the
    pre-completed ``question_interview`` artifact instead (traced, not graded).
    """
    from app.aegis_v1.drafter_client import is_offline_pipeline_client
    from app.aegis_v1.tools import simulator

    attempts = max_attempts if max_attempts is not None else MAX_APPEAL_ATTEMPTS
    if attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    question_responder = None
    if run_question_agent:
        from app.aegis_v1.patient_simulator import GeminiPatientSimulatorClient
        from app.aegis_v1.question_agent import responder_from_simulator

        simulator_client_qa = patient_simulator_client or GeminiPatientSimulatorClient()
        question_responder = responder_from_simulator(
            simulator_client_qa,
            clinical_context=teacher_clinical_context,
            patient_profile=patient_profile,
        )

    best_package: dict[str, Any] | None = None
    best_outcome: dict[str, Any] | None = None

    for attempt in range(1, attempts + 1):
        first_attempt = attempt == 1
        appeal_package = run_aegis_v1_pipeline(
            denial_text=denial_text,
            clinical_context=clinical_context,
            case_id=case_id,
            insurer=insurer,
            patient_age=patient_age,
            patient_gender=patient_gender,
            dataset_split=dataset_split,
            run_mode=run_mode,
            phoenix_mode=phoenix_mode,
            drafter_client=drafter_client,
            library_stack=library_stack,
            drafter_prompt_version=drafter_prompt_version,
            drafter_prompt_text=drafter_prompt_text,
            playbook_override=playbook_override,
            geo_playbook_override=geo_playbook_override,
            use_phoenix_memory=use_phoenix_memory,
            run_question_agent=run_question_agent and first_attempt,
            question_responder=question_responder if first_attempt else None,
            question_agent_client=question_agent_client,
            question_interview=question_interview,
        )
        if first_attempt and run_question_agent:
            # Interview once; carry the artifact + enriched context to retries.
            artifact = appeal_package.get("question_interview") or None
            if artifact:
                question_interview = artifact
                enriched = str(artifact.get("enriched_context") or "")
                if artifact.get("qa_transcript") and enriched:
                    clinical_context = enriched
        if attempt == 1 and phoenix_mode == PhoenixMode.APPEAL:
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
