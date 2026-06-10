from __future__ import annotations

from app.aegis_v1.patient_simulator import (
    PATIENT_REFUSAL,
    PATIENT_UNSURE,
    StubPatientSimulatorClient,
    is_regulatory_question,
)
from app.aegis_v1.question_agent import (
    MAX_QUESTIONS,
    GeminiQuestionAgentClient,
    QuestionDecision,
    StubQuestionAgentClient,
    is_substantive_answer,
    responder_from_simulator,
    run_question_interview,
)
from app.aegis_v1.schemas import QATurn


class RoutingQuestionAgentClient:
    """Agent that owns final substantive vs gap routing on stop."""

    name = "routing_question_agent"

    def decide(self, **kwargs: object) -> QuestionDecision:
        transcript = kwargs["transcript"]  # type: ignore[index]
        symptom_q = "When did your symptoms start, and how do they affect your daily life?"
        treatment_q = "Have you tried other treatments for this before, and what happened?"
        planned = [symptom_q, treatment_q]
        if not transcript:
            return QuestionDecision(
                action="ask",
                question=symptom_q,
                planned_questions=planned,
                gap_analysis="Need symptom timeline.",
            )
        return QuestionDecision(
            action="stop",
            planned_questions=planned,
            gap_analysis="Symptom timeline unresolved.",
            substantive_questions=[],
            gap_questions=[symptom_q, treatment_q],
        )

PLAYBOOK = {
    "insurer": "Cigna",
    "denial_type": "medical_necessity",
    "required_evidence": [
        "clinical notes",
        "prior treatment failures",
        "guideline or plan-language support",  # regulatory -> must NOT become a patient question
    ],
}

DENIAL = "Cigna denied coverage for TMS as not medically necessary."


# --- Skip path ---------------------------------------------------------------

def test_skip_returns_planned_questions_and_no_turns() -> None:
    result = run_question_interview(
        denial_text=DENIAL,
        notes="My doctor recommended this.",
        playbook=PLAYBOOK,
        client=StubQuestionAgentClient(),
        skip=True,
    )
    assert result.skipped is True
    assert result.qa_transcript == []
    assert result.planned_questions  # surfaced for the draft-page gap list
    assert result.patient_gap_note  # plain-English copy present
    # Skip drafts with only the pasted notes — no Q&A appended.
    assert result.enriched_context == "My doctor recommended this."


def test_no_responder_behaves_like_skip() -> None:
    result = run_question_interview(
        denial_text=DENIAL, notes="", playbook=PLAYBOOK, client=StubQuestionAgentClient()
    )
    assert result.skipped is True
    assert result.qa_transcript == []


# --- Full interview ----------------------------------------------------------

def test_full_interview_enriches_context_for_drafter() -> None:
    clinical = (
        "Symptoms started about a year ago and severely affect daily life. "
        "The patient tried two SSRIs before without improvement."
    )
    simulator = StubPatientSimulatorClient(clinical_context=clinical)
    responder = responder_from_simulator(simulator, clinical_context=clinical)

    result = run_question_interview(
        denial_text=DENIAL,
        notes="Patient wants to appeal.",
        playbook=PLAYBOOK,
        responder=responder,
        client=StubQuestionAgentClient(),
    )

    assert result.skipped is False
    assert 1 <= len(result.qa_transcript) <= MAX_QUESTIONS
    # Substantive answers flow into the drafter context.
    assert "PATIENT Q&A:" in result.enriched_context
    assert "Patient wants to appeal." in result.enriched_context


def test_interview_caps_at_max_questions() -> None:
    result = run_question_interview(
        denial_text=DENIAL,
        notes="",
        playbook=PLAYBOOK,
        responder=lambda q: "Yes, here are the details about that.",
        client=StubQuestionAgentClient(),
    )
    assert len(result.qa_transcript) <= MAX_QUESTIONS


# --- Adaptivity: drop resolved, never repeat ---------------------------------

def test_prior_answer_resolves_later_question() -> None:
    # An answer mentioning "treatment" should drop the treatment question.
    transcript = [
        QATurn(
            turn=1,
            question="When did your symptoms start, and how do they affect your daily life?",
            answer="They started a year ago. I have also tried other treatment already.",
        )
    ]
    decision = StubQuestionAgentClient().decide(
        denial_text=DENIAL,
        notes="",
        playbook=PLAYBOOK,
        phoenix_summary={},
        transcript=transcript,
    )
    treatment_q = "Have you tried other treatments for this before, and what happened?"
    if decision.action == "ask":
        assert decision.question != treatment_q


def test_no_repeat_after_dont_know() -> None:
    symptom_q = "When did your symptoms start, and how do they affect your daily life?"
    transcript = [QATurn(turn=1, question=symptom_q, answer="I don't know")]
    decision = StubQuestionAgentClient().decide(
        denial_text=DENIAL,
        notes="",
        playbook=PLAYBOOK,
        phoenix_summary={},
        transcript=transcript,
    )
    assert decision.action == "ask"
    assert decision.question != symptom_q  # do not re-ask the same question


def test_dont_know_is_not_substantive() -> None:
    assert is_substantive_answer("I don't know") is False
    assert is_substantive_answer("") is False
    assert is_substantive_answer("Not sure.") is False
    assert is_substantive_answer(PATIENT_UNSURE) is False
    assert is_substantive_answer("Yes, I tried two SSRIs.") is True


def test_patient_unsure_routes_to_gap_not_drafter_context() -> None:
    symptom_q = "When did your symptoms start, and how do they affect your daily life?"
    result = run_question_interview(
        denial_text=DENIAL,
        notes="Patient wants to appeal.",
        playbook=PLAYBOOK,
        responder=lambda question: (
            PATIENT_UNSURE
            if question == symptom_q
            else "Yes, I tried two SSRIs without improvement."
        ),
        client=StubQuestionAgentClient(),
    )

    assert symptom_q in result.patient_gap_note
    assert PATIENT_UNSURE not in result.enriched_context
    assert "SSRI" in result.enriched_context


def test_enriched_context_includes_full_transcript_when_agent_omits_substantive_tags() -> None:
    """Regression: drafter must get Q&A even if the model leaves substantive_questions empty."""
    seizure_q = "Do you have a history of withdrawal seizures?"
    result = run_question_interview(
        denial_text=DENIAL,
        notes="Patient wants to appeal.",
        playbook=PLAYBOOK,
        responder=lambda question: "I had a seizure during withdrawal two years ago.",
        client=RoutingQuestionAgentClient(),
    )

    assert result.substantive_questions  # derived from transcript, not agent tags
    assert "PATIENT Q&A:" in result.enriched_context
    assert "seizure" in result.enriched_context.lower()


def test_finalize_trusts_agent_routing_on_stop() -> None:
    symptom_q = "When did your symptoms start, and how do they affect your daily life?"
    result = run_question_interview(
        denial_text=DENIAL,
        notes="Patient wants to appeal.",
        playbook=PLAYBOOK,
        responder=lambda question: PATIENT_UNSURE,
        client=RoutingQuestionAgentClient(),
    )

    assert symptom_q in result.gap_questions
    assert result.substantive_questions == []
    assert PATIENT_UNSURE not in result.enriched_context
    assert symptom_q in result.patient_gap_note


def test_stub_decision_returns_agent_classification_fields() -> None:
    symptom_q = "When did your symptoms start, and how do they affect your daily life?"
    transcript = [QATurn(turn=1, question=symptom_q, answer="I don't know")]
    decision = StubQuestionAgentClient().decide(
        denial_text=DENIAL,
        notes="",
        playbook=PLAYBOOK,
        phoenix_summary={},
        transcript=transcript,
    )

    assert symptom_q in decision.gap_questions
    assert symptom_q not in decision.substantive_questions


# --- Simulator firewall ------------------------------------------------------

def test_simulator_refuses_regulatory_question() -> None:
    simulator = StubPatientSimulatorClient(
        clinical_context="ERISA section 1133 requires a full and fair review."
    )
    answer = simulator.answer(
        question="What does ERISA say about the medical necessity standard?",
        clinical_context="ERISA section 1133 requires a full and fair review.",
    )
    assert answer == PATIENT_REFUSAL
    assert "ERISA" not in answer


def test_simulator_answers_patient_question_from_context() -> None:
    clinical = "The patient tried two SSRIs before without improvement."
    simulator = StubPatientSimulatorClient(clinical_context=clinical)
    answer = simulator.answer(
        question="Have you tried other treatments for this before, and what happened?",
        clinical_context=clinical,
    )
    assert answer != PATIENT_REFUSAL
    assert "SSRI" in answer


def test_is_regulatory_question_detects_policy_terms() -> None:
    assert is_regulatory_question("What is the plan language on step therapy?") is True
    assert is_regulatory_question("What is the filing deadline?") is True
    assert is_regulatory_question("When did your symptoms start?") is False


# --- Live client construction (offline; no network) --------------------------

def test_gemini_question_agent_constructs_offline() -> None:
    client = GeminiQuestionAgentClient()
    assert client.name == "gemini_question_agent"
