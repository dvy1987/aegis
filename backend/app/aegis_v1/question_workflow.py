"""Pre-draft interview orchestration.

Sits in the orchestration/eval layer (like the Outcome Simulator), NOT inside the
Student — so the question agent can run before drafting on:

- **showcase**: the patient simulator is given the teacher's full clinical file
  and answers in a patient's voice; the drafter only ever sees the enriched
  patient-knowable context (firewall INV-QA preserved).
- **appeal** (Phase 2): a real-user ``responder`` is supplied instead of a
  simulator.

The Student/drafter is fed ``QuestionInterviewResult.enriched_context`` — the
patient's age/gender plus substantive Q&A answers — never the raw teacher file.
"""

from __future__ import annotations

from typing import Any

from app.aegis_v1.patient_simulator import PatientSimulatorClient
from app.aegis_v1.question_agent import (
    MAX_QUESTIONS,
    QuestionAgentClient,
    Responder,
    responder_from_simulator,
    run_question_interview,
)
from app.aegis_v1.schemas import QuestionInterviewResult


def run_pre_draft_interview(
    *,
    denial_text: str,
    base_clinical_context: str = "",
    teacher_clinical_context: str = "",
    patient_profile: dict[str, Any] | None = None,
    playbook: dict[str, Any] | None = None,
    phoenix_summary: dict[str, Any] | None = None,
    question_agent_client: QuestionAgentClient | None = None,
    patient_simulator_client: PatientSimulatorClient | None = None,
    responder: Responder | None = None,
    skip: bool = False,
    max_questions: int = MAX_QUESTIONS,
) -> QuestionInterviewResult:
    """Run the pre-draft interview and return its result.

    - ``base_clinical_context`` is the student-visible seed (age/gender). It
      becomes the interview "notes" and the base of the enriched context.
    - ``teacher_clinical_context`` is the full synthetic clinical file. It is
      handed ONLY to the patient simulator (showcase), never to the drafter.
    - On appeal, pass an explicit ``responder`` (real user) instead of relying on
      the simulator.
    """
    if responder is None and not skip:
        from app.aegis_v1.patient_simulator import GeminiPatientSimulatorClient

        simulator = patient_simulator_client or GeminiPatientSimulatorClient()
        responder = responder_from_simulator(
            simulator,
            clinical_context=teacher_clinical_context,
            patient_profile=patient_profile,
        )

    if question_agent_client is None:
        from app.aegis_v1.question_agent import GeminiQuestionAgentClient

        question_agent_client = GeminiQuestionAgentClient()

    return run_question_interview(
        denial_text=denial_text,
        notes=base_clinical_context,
        playbook=playbook,
        phoenix_summary=phoenix_summary,
        responder=responder,
        client=question_agent_client,
        skip=skip,
        max_questions=max_questions,
    )
