"""INV-QA firewall + turn-based session tests (question agent Phases 2 & 7).

INV-QA: in showcase, the Student/question agent NEVER sees the teacher's full
clinical file. Only the patient simulator is seeded with it, answers in a
patient voice, and refuses regulatory content — so teacher-only material can
only cross the firewall as patient-knowable facts. Mirrors the INV-2 style of
build-breaking assertions.
"""

from __future__ import annotations

from typing import Any

from app.aegis_v1.patient_simulator import PATIENT_REFUSAL, StubPatientSimulatorClient
from app.aegis_v1.question_agent import MAX_QUESTIONS, StubQuestionAgentClient
from app.aegis_v1.question_session import QuestionSessionStore
from app.aegis_v1.question_workflow import run_pre_draft_interview

# Teacher-only sentinel embedded in a regulatory sentence: the simulator must
# never quote it, and the question agent must never receive it as input.
SENTINEL = "INTERNAL-ANSWER-KEY-XYZZY"
TEACHER_CONTEXT = (
    "Symptoms started a year ago and severely affect daily life. "
    f"Coverage criteria statute regulation {SENTINEL}."
)
BASE_CONTEXT = "Patient is 44F; wants to appeal."
DENIAL = "Cigna denied TMS as not medically necessary."
PLAYBOOK = {
    "insurer": "Cigna",
    "denial_type": "medical_necessity",
    "required_evidence": ["clinical notes", "prior treatment failures"],
}


class RecordingQuestionAgent(StubQuestionAgentClient):
    """Stub agent that records every input it is shown (firewall probe)."""

    def __init__(self) -> None:
        self.seen_notes: list[str] = []
        self.seen_playbooks: list[dict[str, Any]] = []

    def decide(
        self, *, denial_text, notes, playbook, phoenix_summary, transcript, library_context=""
    ):
        self.seen_notes.append(notes)
        self.seen_playbooks.append(playbook)
        return super().decide(
            denial_text=denial_text,
            notes=notes,
            playbook=playbook,
            phoenix_summary=phoenix_summary,
            transcript=transcript,
            library_context=library_context,
        )


# --- INV-QA: showcase firewall ------------------------------------------------

def test_inv_qa_question_agent_never_sees_teacher_context() -> None:
    agent = RecordingQuestionAgent()
    run_pre_draft_interview(
        denial_text=DENIAL,
        base_clinical_context=BASE_CONTEXT,
        teacher_clinical_context=TEACHER_CONTEXT,
        playbook=PLAYBOOK,
        question_agent_client=agent,
        patient_simulator_client=StubPatientSimulatorClient(),
    )
    assert agent.seen_notes, "interview must consult the agent at least once"
    for notes in agent.seen_notes:
        assert SENTINEL not in notes
        assert notes == BASE_CONTEXT  # agent sees ONLY the student-visible seed
    for playbook in agent.seen_playbooks:
        assert SENTINEL not in str(playbook)


def test_inv_qa_enriched_context_never_carries_teacher_regulatory_text() -> None:
    result = run_pre_draft_interview(
        denial_text=DENIAL,
        base_clinical_context=BASE_CONTEXT,
        teacher_clinical_context=TEACHER_CONTEXT,
        playbook=PLAYBOOK,
        question_agent_client=StubQuestionAgentClient(),
        patient_simulator_client=StubPatientSimulatorClient(),
    )
    # The drafter input may contain patient-voiced facts, never the sentinel.
    assert SENTINEL not in result.enriched_context
    assert SENTINEL not in result.patient_gap_note
    for turn in result.qa_transcript:
        assert SENTINEL not in turn.answer


def test_inv_qa_simulator_refusal_blocks_regulatory_leak() -> None:
    simulator = StubPatientSimulatorClient(clinical_context=TEACHER_CONTEXT)
    answer = simulator.answer(
        question="What coverage criteria or statute applies here?",
        clinical_context=TEACHER_CONTEXT,
    )
    assert answer == PATIENT_REFUSAL
    assert SENTINEL not in answer


# --- Phase 2: turn-based session (appeal flow) --------------------------------

def test_session_turn_flow_finalizes_with_enriched_context() -> None:
    store = QuestionSessionStore()
    session = store.start(
        denial_text=DENIAL,
        notes=BASE_CONTEXT,
        playbook=PLAYBOOK,
        client=StubQuestionAgentClient(),
    )
    assert not session.done
    assert session.pending_question

    turns = 0
    while not session.done and turns < MAX_QUESTIONS + 1:
        session = store.answer(session.interview_id, "Yes — here are the details.")
        turns += 1

    assert session.done
    result = session.result
    assert result is not None
    assert result.skipped is False
    assert 1 <= len(result.qa_transcript) <= MAX_QUESTIONS
    assert "PATIENT Q&A:" in result.enriched_context
    assert BASE_CONTEXT in result.enriched_context


def test_session_skip_surfaces_planned_questions_as_gaps() -> None:
    store = QuestionSessionStore()
    session = store.start(
        denial_text=DENIAL,
        notes=BASE_CONTEXT,
        playbook=PLAYBOOK,
        client=StubQuestionAgentClient(),
    )
    session = store.skip(session.interview_id)
    result = session.result
    assert result is not None
    assert result.skipped is True
    assert result.qa_transcript == []
    assert result.planned_questions
    assert result.patient_gap_note
    assert result.enriched_context == BASE_CONTEXT  # notes only, no Q&A


def test_session_never_repeats_a_question() -> None:
    store = QuestionSessionStore()
    session = store.start(
        denial_text=DENIAL,
        notes="",
        playbook=PLAYBOOK,
        client=StubQuestionAgentClient(),
    )
    asked: list[str] = []
    turns = 0
    while not session.done and turns < MAX_QUESTIONS + 1:
        asked.append(session.pending_question)
        session = store.answer(session.interview_id, "I don't know")
        turns += 1
    assert len(asked) == len(set(asked))
