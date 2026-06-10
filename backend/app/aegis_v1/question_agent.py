"""Pre-draft question agent (v1).

Runs **before** the drafter on both `/appeal` (real user) and showcase (patient
simulator). It reads the denial + optional notes, having already consulted the
playbook + Phoenix memory during prep, then runs an **adaptive interview** of up
to 5 questions. It asks ONLY patient-knowable facts; regulatory/policy gaps are
looked up via playbook/library and are never asked of the patient.

Design: docs/specs/2026-06-10-question-agent-design.md.

Patterns mirror `drafter_client` / `simulator_client`: a `Protocol` + a
deterministic offline `Stub*` + a live `Gemini*`. The evolvable prompt component
id is **`question_agent_system_prompt`** (pinned; learning loop mutates it).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Literal, Protocol

from pydantic import BaseModel, Field

from app.aegis_v1.patient_simulator import (
    PatientSimulatorClient,
    is_regulatory_question,
)
from app.aegis_v1.schemas import QATurn, QuestionInterviewResult

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
ACTIVE_QUESTION_PROMPT_FILE = PROMPT_DIR / "active_question_agent_prompt.txt"
QUESTION_AGENT_COMPONENT_ID = "question_agent_system_prompt"
MAX_QUESTIONS = 5

# Answers that carry no usable patient fact — do not feed the drafter, and surface
# the question as a gap instead.
_NON_ANSWERS = (
    "i don't know",
    "i dont know",
    "idk",
    "not sure",
    "no idea",
    "unsure",
    "n/a",
    "na",
    "",
)

Responder = Callable[[str], str]


def load_question_agent_prompt(version: str = "question_agent_v1") -> str:
    return (PROMPT_DIR / f"{version}.md").read_text(encoding="utf-8")


def get_active_question_agent_prompt_version() -> str:
    configured = os.environ.get("AEGIS_QUESTION_AGENT_PROMPT_VERSION")
    if configured:
        return configured
    if ACTIVE_QUESTION_PROMPT_FILE.exists():
        value = ACTIVE_QUESTION_PROMPT_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "question_agent_v1"


def is_substantive_answer(answer: str) -> bool:
    """Fallback heuristic when the agent omits classification (e.g. question judge)."""
    return not _is_non_answer(answer)


def _is_non_answer(answer: str) -> bool:
    from app.aegis_v1.patient_simulator import PATIENT_UNSURE

    normalized = (answer or "").strip().lower().rstrip(".!")
    if not normalized:
        return True
    if normalized == PATIENT_UNSURE.strip().lower().rstrip(".!"):
        return True
    if normalized in _NON_ANSWERS:
        return True
    if "don't know" in normalized or "dont know" in normalized:
        return True
    if "not totally sure" in normalized or "not sure" in normalized:
        return True
    return False


class QuestionDecision(BaseModel):
    """One step of the adaptive interview.

    ``planned_questions`` is the agent's current best full plan (used for the
    skip / gap list). On ``stop``, ``substantive_questions`` and
    ``gap_questions`` are the agent's final routing: which asked questions feed
    the drafter vs surface as patient-facing gaps. ``gap_analysis`` is
    internal-only (judges/Phoenix).
    """

    action: Literal["ask", "stop"]
    question: str = ""
    planned_questions: list[str] = Field(default_factory=list)
    gap_analysis: str = ""
    substantive_questions: list[str] = Field(default_factory=list)
    gap_questions: list[str] = Field(default_factory=list)


class QuestionAgentClient(Protocol):
    name: str

    def decide(
        self,
        *,
        denial_text: str,
        notes: str,
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        transcript: list[QATurn],
        library_context: str = "",
    ) -> QuestionDecision:
        """Decide the next interview step given everything known so far.

        ``playbook`` may be a single playbook OR an insurer-wide bundle
        (``{"insurer": ..., "playbooks": [...]}``) — on appeal the denial type
        is unknown a priori, so the agent gets every playbook for the insurer.
        ``library_context`` carries library/corpus excerpts so the agent never
        asks the patient something a lookup already answers.
        """


# --- Deterministic candidate generation (shared by the stub) -----------------

# Always-on patient questions (keyword used for "already resolved" detection).
_BASE_SPECS: list[tuple[str, str]] = [
    ("symptom", "When did your symptoms start, and how do they affect your daily life?"),
    ("treatment", "Have you tried other treatments for this before, and what happened?"),
]
# Regulatory evidence the agent must NOT ask the patient about.
_REGULATORY_EVIDENCE = (
    "guideline",
    "plan-language",
    "plan language",
    "policy",
    "statute",
    "regulation",
    "authorization request record",
)


def _evidence_to_question(evidence: str) -> tuple[str, str]:
    """Map a playbook ``required_evidence`` item to a patient-knowable question.

    Returns ``("", "")`` for regulatory items the patient cannot answer.
    """
    low = evidence.lower()
    if any(term in low for term in _REGULATORY_EVIDENCE):
        return ("", "")
    if "letter" in low:
        return (
            "doctor letter",
            "Has your doctor written a letter explaining why you need this treatment?",
        )
    if "treatment" in low:
        return (
            "treatment",
            "Have you tried other treatments for this before, and what happened?",
        )
    if "record" in low or "notes" in low or "history" in low:
        return (
            "records",
            "Do you have recent medical records or test results for this condition?",
        )
    if "diagnosis" in low:
        return ("diagnosis", "What diagnosis did your doctor give you?")
    return ("", "")


def _bundle_playbooks(playbook: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize a single playbook OR an insurer-wide bundle to a list."""
    nested = playbook.get("playbooks")
    if isinstance(nested, list):
        return [pb for pb in nested if isinstance(pb, dict)]
    return [playbook]


def candidate_specs(
    denial_text: str,
    notes: str,
    playbook: dict[str, Any],
) -> list[tuple[str, str]]:
    """Deterministic ordered (keyword, question) candidates, capped at MAX_QUESTIONS."""
    specs: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(keyword: str, question: str) -> None:
        if question and question not in seen:
            seen.add(question)
            specs.append((keyword, question))

    for keyword, question in _BASE_SPECS:
        add(keyword, question)
    for pb in _bundle_playbooks(playbook):
        for evidence in pb.get("required_evidence") or []:
            add(*_evidence_to_question(str(evidence)))
    add("", "Is there anything the denial letter got wrong or left out about your situation?")
    return specs[:MAX_QUESTIONS]


class StubQuestionAgentClient:
    """Deterministic offline question agent for tests/dry-runs.

    Plans from playbook required-evidence + a couple of always-on patient
    questions, then adapts: it skips questions already asked and questions a
    prior substantive answer has already resolved (keyword match).
    """

    name = "stub_question_agent"

    def decide(
        self,
        *,
        denial_text: str,
        notes: str,
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        transcript: list[QATurn],
        library_context: str = "",
    ) -> QuestionDecision:
        specs = candidate_specs(denial_text, notes, playbook)
        planned = [question for _, question in specs]
        asked = {turn.question for turn in transcript}
        substantive, gaps = classify_interview(
            planned_questions=planned,
            transcript=transcript,
        )
        answered_text = " ".join(
            turn.answer.lower()
            for turn in transcript
            if turn.question in substantive
        )

        remaining: list[str] = []
        for keyword, question in specs:
            if question in asked:
                continue
            if keyword and all(tok in answered_text for tok in keyword.split()):
                continue  # a prior answer already resolved this line of inquiry
            remaining.append(question)

        gap = _gap_analysis(remaining)
        if not remaining or len(transcript) >= MAX_QUESTIONS:
            return QuestionDecision(
                action="stop",
                planned_questions=planned,
                gap_analysis=gap,
                substantive_questions=substantive,
                gap_questions=gaps,
            )
        return QuestionDecision(
            action="ask",
            question=remaining[0],
            planned_questions=planned,
            gap_analysis=gap,
            substantive_questions=substantive,
            gap_questions=gaps,
        )


def _gap_analysis(remaining: list[str]) -> str:
    if not remaining:
        return "All planned patient questions were covered."
    return "Unresolved patient questions: " + "; ".join(remaining)


class GeminiQuestionAgentClient:
    """Vertex/Gemini-backed adaptive question agent. Construction is unit-tested
    offline; live generation runs in a GCP session. Falls back to the stub's
    decision if the model call fails so a run never stalls."""

    name = "gemini_question_agent"

    def __init__(
        self,
        model: str | None = None,
        location: str | None = None,
        prompt_version: str | None = None,
        prompt_text: str | None = None,
    ) -> None:
        self.model = model or os.environ.get(
            "AEGIS_QUESTION_AGENT_MODEL", "gemini-3.1-pro-preview"
        )
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        self._prompt_version = prompt_version
        self._prompt_text = prompt_text

    def _system_prompt(self) -> str:
        if self._prompt_text is not None:
            return self._prompt_text
        version = self._prompt_version or get_active_question_agent_prompt_version()
        return load_question_agent_prompt(version)

    def decide(
        self,
        *,
        denial_text: str,
        notes: str,
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        transcript: list[QATurn],
        library_context: str = "",
    ) -> QuestionDecision:
        try:
            from google import genai
            from google.genai import types

            from app.gemini_retry import generate_content_with_fallback

            class _Decision(BaseModel):
                action: Literal["ask", "stop"]
                question: str = ""
                planned_questions: list[str] = Field(default_factory=list)
                gap_analysis: str = ""
                substantive_questions: list[str] = Field(default_factory=list)
                gap_questions: list[str] = Field(default_factory=list)

            contents = self._build_contents(
                denial_text=denial_text,
                notes=notes,
                playbook=playbook,
                phoenix_summary=phoenix_summary,
                transcript=transcript,
                library_context=library_context,
            )
            client = genai.Client(vertexai=True, location=self.location)
            response = generate_content_with_fallback(
                client.models.generate_content,
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_Decision,
                    temperature=0.3,
                ),
            )
            data = json.loads(response.text)
            decision = QuestionDecision.model_validate(data)
            decision = _with_resolved_classification(
                decision,
                planned_questions=decision.planned_questions or candidate_specs(
                    denial_text, notes, playbook
                )[:MAX_QUESTIONS],
                transcript=transcript,
            )
            # Firewall: never ask the patient a regulatory question.
            if decision.action == "ask" and is_regulatory_question(decision.question):
                return StubQuestionAgentClient().decide(
                    denial_text=denial_text,
                    notes=notes,
                    playbook=playbook,
                    phoenix_summary=phoenix_summary,
                    transcript=transcript,
                )
            return decision
        except Exception:
            logging.getLogger(__name__).warning(
                "GeminiQuestionAgentClient.decide failed; falling back to stub plan",
                exc_info=True,
            )
            return StubQuestionAgentClient().decide(
                denial_text=denial_text,
                notes=notes,
                playbook=playbook,
                phoenix_summary=phoenix_summary,
                transcript=transcript,
            )

    def _build_contents(
        self,
        *,
        denial_text: str,
        notes: str,
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        transcript: list[QATurn],
        library_context: str = "",
    ) -> str:
        transcript_text = "\n".join(
            f"Q{turn.turn}: {turn.question}\nA{turn.turn}: {turn.answer}"
            for turn in transcript
        )
        return (
            f"{self._system_prompt()}\n\n"
            f"DENIAL LETTER:\n{denial_text.strip()}\n\n"
            f"PATIENT NOTES (optional):\n{notes.strip() or '(none)'}\n\n"
            "INSURER PLAYBOOKS (internal; complete bundle — denial type is not "
            f"known a priori):\n{json.dumps(playbook, default=str)}\n\n"
            f"PHOENIX MEMORY (internal):\n{json.dumps(phoenix_summary, default=str)}\n\n"
            f"LIBRARY EXCERPTS (internal):\n{library_context.strip() or '(none)'}\n\n"
            f"INTERVIEW SO FAR:\n{transcript_text or '(no questions asked yet)'}\n\n"
            "Decide the next step. If the playbooks, Phoenix memory, or library "
            "excerpts already answer a candidate question, do NOT ask it — ask a "
            "fresher, more meaningful patient-knowable question instead, or stop. "
            "Ask at most one more question. Never ask the patient about "
            "regulatory/policy/legal content."
        )


def responder_from_simulator(
    simulator: PatientSimulatorClient,
    *,
    clinical_context: str,
    patient_profile: dict[str, Any] | None = None,
) -> Responder:
    """Bind a patient simulator into a single-arg responder for the interview loop."""

    def _respond(question: str) -> str:
        return simulator.answer(
            question=question,
            clinical_context=clinical_context,
            patient_profile=patient_profile,
        )

    return _respond


def classify_interview(
    *,
    planned_questions: list[str],
    transcript: list[QATurn],
    substantive_questions: list[str] | None = None,
    gap_questions: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Return (substantive_questions, gap_questions) for drafter vs gap-note routing."""
    asked = {turn.question for turn in transcript}
    if substantive_questions is not None or gap_questions is not None:
        substantive = [q for q in (substantive_questions or []) if q in asked]
        gaps = list(gap_questions or [])
        if substantive or gaps:
            not_asked = [question for question in planned_questions if question not in asked]
            gaps = list(dict.fromkeys(gaps + not_asked))
            gaps = [question for question in gaps if question not in substantive]
            return substantive, gaps
    return _derive_classification(planned_questions, transcript)


def _derive_classification(
    planned_questions: list[str],
    transcript: list[QATurn],
) -> tuple[list[str], list[str]]:
    answered = {turn.question for turn in transcript}
    substantive = [
        turn.question for turn in transcript if not _is_non_answer(turn.answer)
    ]
    dont_know = [
        turn.question for turn in transcript if _is_non_answer(turn.answer)
    ]
    not_asked = [question for question in planned_questions if question not in answered]
    gaps = list(dict.fromkeys(not_asked + dont_know))
    return substantive, gaps


def _with_resolved_classification(
    decision: QuestionDecision,
    *,
    planned_questions: list[str],
    transcript: list[QATurn],
) -> QuestionDecision:
    """Use agent classification when present; derive when the model omits fields."""
    planned = list(decision.planned_questions or planned_questions)[:MAX_QUESTIONS]
    substantive, gaps = classify_interview(
        planned_questions=planned,
        transcript=transcript,
        substantive_questions=decision.substantive_questions or None,
        gap_questions=decision.gap_questions or None,
    )
    return decision.model_copy(
        update={
            "planned_questions": planned,
            "substantive_questions": substantive,
            "gap_questions": gaps,
        }
    )


def build_enriched_context(
    notes: str,
    transcript: list[QATurn],
    *,
    substantive_questions: list[str] | None = None,
) -> str:
    """Patient-knowable text for the drafter: notes + agent-approved Q&A only."""
    base = (notes or "").strip()
    substantive_set = set(substantive_questions or [])
    qa_lines = [
        f"Q: {turn.question}\nA: {turn.answer.strip()}"
        for turn in transcript
        if turn.question in substantive_set
    ]
    if not qa_lines:
        return base
    qa_block = "PATIENT Q&A:\n" + "\n".join(qa_lines)
    return f"{base}\n\n{qa_block}".strip()


def finalize_interview_result(
    *,
    notes: str,
    transcript: list[QATurn],
    planned_questions: list[str],
    decision: QuestionDecision,
    skipped: bool,
    gap_analysis: str,
) -> QuestionInterviewResult:
    """Build the interview artifact from the agent's final classification."""
    planned = list(planned_questions)[:MAX_QUESTIONS]
    if skipped and not transcript:
        return QuestionInterviewResult(
            qa_transcript=[],
            enriched_context=(notes or "").strip(),
            planned_questions=planned,
            patient_gap_note=build_patient_gap_note(planned),
            internal_gap_analysis=gap_analysis,
            skipped=True,
        )

    substantive, gaps = classify_interview(
        planned_questions=planned,
        transcript=transcript,
        substantive_questions=decision.substantive_questions,
        gap_questions=decision.gap_questions,
    )
    return QuestionInterviewResult(
        qa_transcript=list(transcript),
        enriched_context=build_enriched_context(
            notes, transcript, substantive_questions=substantive
        ),
        planned_questions=planned,
        patient_gap_note=build_patient_gap_note(gaps),
        internal_gap_analysis=gap_analysis,
        skipped=skipped,
    )


def build_patient_gap_note(gap_questions: list[str]) -> str:
    """Plain-English draft-page copy. Never goes into the appeal letter."""
    if not gap_questions:
        return ""
    lines = [
        "We drafted your appeal with the information available. "
        "Answers to these questions could make it stronger:"
    ]
    lines.extend(f"- {question}" for question in gap_questions)
    return "\n".join(lines)


def run_question_interview(
    *,
    denial_text: str,
    notes: str = "",
    playbook: dict[str, Any] | None = None,
    phoenix_summary: dict[str, Any] | None = None,
    library_context: str = "",
    responder: Responder | None = None,
    client: QuestionAgentClient | None = None,
    skip: bool = False,
    max_questions: int = MAX_QUESTIONS,
) -> QuestionInterviewResult:
    """Run the adaptive pre-draft interview.

    - ``responder`` answers each question (real user adapter on appeal; a
      simulator-bound responder on showcase). When it is ``None`` or ``skip`` is
      set, no questions are asked: the planned questions are still computed for
      the draft-page gap list.
    - The agent asks up to ``max_questions`` patient-knowable questions, dropping
      ones a prior answer resolved and never repeating a question.
    """
    playbook = playbook or {}
    phoenix_summary = phoenix_summary or {}
    active: QuestionAgentClient = client or GeminiQuestionAgentClient()

    transcript: list[QATurn] = []
    first = active.decide(
        denial_text=denial_text,
        notes=notes,
        playbook=playbook,
        phoenix_summary=phoenix_summary,
        transcript=transcript,
        library_context=library_context,
    )
    planned = list(first.planned_questions)[:max_questions]

    if skip or responder is None:
        return finalize_interview_result(
            notes=notes,
            transcript=[],
            planned_questions=planned,
            decision=first,
            skipped=True,
            gap_analysis=first.gap_analysis,
        )

    decision = first
    while (
        decision.action == "ask"
        and decision.question
        and len(transcript) < max_questions
    ):
        question = decision.question
        if any(turn.question == question for turn in transcript):
            break  # never repeat a question
        answer = responder(question) or ""
        transcript.append(
            QATurn(turn=len(transcript) + 1, question=question, answer=answer)
        )
        decision = active.decide(
            denial_text=denial_text,
            notes=notes,
            playbook=playbook,
            phoenix_summary=phoenix_summary,
            transcript=transcript,
            library_context=library_context,
        )

    decision = _with_resolved_classification(
        decision,
        planned_questions=planned,
        transcript=transcript,
    )
    return finalize_interview_result(
        notes=notes,
        transcript=transcript,
        planned_questions=planned,
        decision=decision,
        skipped=False,
        gap_analysis=decision.gap_analysis,
    )
