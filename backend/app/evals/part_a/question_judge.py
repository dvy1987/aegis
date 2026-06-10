"""Question-agent judge — an LLM agent with a deterministic offline fallback.

Two jobs (showcase only — synthetic cases embed regulatory/insurer/legal facts
in the hidden teacher clinical file):

1. **Part A — conversation quality (grading)**: rate the whole transcript —
   did the agent ask the right patient-knowable questions, make a best effort
   to get the relevant answers, avoid repeats/waste, and never ask the patient
   regulatory questions?
2. **Part B — playbook gap mining (NOT grading)**: pull the regulatory /
   legal / insurer-specific facts out of the hidden teacher clinical file (a
   patient would never know these; the system does not have them yet), decide
   which playbook each belongs to — global vs the insurer slice with
   sub-tactic — and emit detailed append-first instructions. These ride the
   panel metadata + the laundered improvement note into Phoenix, so the GEPA
   loop pulls these learnings automatically when reflecting on playbooks.

Appeal = traced, not graded: with no interview artifact the judge returns the
neutral default and ``graded=False``.

``GeminiQuestionJudgeClient`` is the live LLM judge (structured output); the
deterministic offline judge keeps tests/dry-runs working and is the fallback
whenever the model call fails.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from pydantic import BaseModel, Field

from app.aegis_v1.patient_simulator import is_regulatory_question
from app.aegis_v1.question_agent import is_substantive_answer
from app.evals.part_a.schemas import JudgeResult, TeacherGradingPacket

logger = logging.getLogger(__name__)

MAX_PLAYBOOK_ADDITIONS = 5

# Playbook-mining notes belong in playbook reflection — never question-agent prompt mutation.
_PLAYBOOK_NOTE_MARKERS = (
    "playbook addition",
    "add to playbook",
    "add to global playbook",
)

_PATIENT_ASK_MARKERS = (
    "ask the patient",
    "ask patient",
    "ask them",
    "ask about",
    "ask whether",
    "interview the patient about",
)


def advises_regulatory_patient_ask(text: str) -> bool:
    """True when text tells GEPA to have the question agent ask regulatory facts."""
    low = (text or "").strip().lower()
    if not low:
        return False
    if any(marker in low for marker in _PLAYBOOK_NOTE_MARKERS):
        return True
    has_patient_ask = any(marker in low for marker in _PATIENT_ASK_MARKERS)
    if not has_patient_ask:
        return False
    if is_regulatory_question(low):
        return True
    return any(
        term in low
        for term in (
            "regulatory",
            "policy",
            "legal",
            "statute",
            "coverage criteria",
            "plan language",
            "filing deadline",
            "appeal rights",
            "clinical guideline",
        )
    )


def filter_question_agent_reflection_notes(notes: list[str]) -> list[str]:
    """Drop judge notes that would steer GEPA to weaken the regulatory firewall."""
    return [n for n in notes if n.strip() and not advises_regulatory_patient_ask(n)]


def sanitize_question_agent_improvement(
    improvement: str | None,
    *,
    playbook_additions: list[str],
) -> str | None:
    """Launder improvement for Phoenix/GEPA — playbook facts go to playbooks only."""
    if playbook_additions:
        return "Playbook additions (append-first): " + "; ".join(playbook_additions)
    cleaned = (improvement or "").strip()
    if not cleaned or advises_regulatory_patient_ask(cleaned):
        return None
    return cleaned


class QuestionJudgeOutput(BaseModel):
    result: JudgeResult
    playbook_additions: list[str] = Field(default_factory=list)
    graded: bool = False
    substantive_questions: list[str] = Field(default_factory=list)
    gap_questions: list[str] = Field(default_factory=list)


def _neutral_result(reasoning: str) -> JudgeResult:
    return JudgeResult(
        dimension="question_agent",
        reasoning=reasoning,
        score=5,
        confidence=1.0,
        evidence_quotes=[],
        improvement=None,
    )


def _slice_key(teacher: TeacherGradingPacket) -> str:
    from app.learning.slice_key import format_slice_key

    sub_tactic = str((teacher.matrix_cell or {}).get("sub_tactic") or "unknown")
    return format_slice_key(teacher.insurer, teacher.denial_type, sub_tactic)


def _regulatory_sentences(clinical_context: str) -> list[str]:
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", clinical_context or "")
        if s.strip()
    ]
    return [s for s in sentences if is_regulatory_question(s)]


_INSURER_SPECIFIC_TERMS = ("plan", "policy", "coverage criteria", "prior authorization")


def extract_playbook_additions(teacher: TeacherGradingPacket | None) -> list[str]:
    """Part B (offline): mine regulatory/insurer/legal facts embedded in the
    synthetic teacher clinical file into targeted append-first instructions."""
    if teacher is None:
        return []
    additions: list[str] = []
    slice_key = _slice_key(teacher)
    insurer_low = (teacher.insurer or "").lower()
    for sentence in _regulatory_sentences(teacher.clinical_context)[:MAX_PLAYBOOK_ADDITIONS]:
        low = sentence.lower()
        insurer_specific = (bool(insurer_low) and insurer_low in low) or any(
            term in low for term in _INSURER_SPECIFIC_TERMS
        )
        target = f"playbook:{slice_key}" if insurer_specific else "global playbook"
        additions.append(
            f"Add to {target} (append-first; verify not already covered): {sentence}"
        )
    return additions


def _grade_transcript(question_interview: dict[str, Any]) -> tuple[int, str, list[str]]:
    """Part A (offline): anchor score + reasoning for the whole transcript."""
    transcript = list(question_interview.get("qa_transcript") or [])
    skipped = bool(question_interview.get("skipped"))
    questions = [str(t.get("question", "")) for t in transcript]
    answers = [str(t.get("answer", "")) for t in transcript]

    regulatory = [q for q in questions if is_regulatory_question(q)]
    substantive = [a for a in answers if is_substantive_answer(a)]
    repeated = len(questions) != len(set(questions))

    if regulatory:
        return (
            1,
            "Firewall breach: the agent asked the patient a regulatory/policy "
            f"question ({regulatory[0]!r}). Regulatory gaps must be looked up "
            "via playbook/library/Phoenix, never asked of the patient.",
            questions,
        )
    if skipped:
        return (
            3,
            "Interview skipped: planned questions were surfaced as draft-page "
            "gaps, but no patient facts were gathered before drafting.",
            questions,
        )
    if not transcript:
        return (
            3,
            "The agent asked no questions. Acceptable only when prep sources "
            "(playbooks/Phoenix/library) already covered the planned lines of inquiry.",
            questions,
        )
    if len(substantive) >= 2 and not repeated:
        return (
            5,
            f"Interview gathered {len(substantive)} substantive patient answers "
            f"over {len(transcript)} turns with no repeats and no regulatory "
            "questions; full transcript passed to the drafter.",
            questions,
        )
    if len(substantive) >= 1:
        return (
            3,
            f"Interview ran {len(transcript)} turns but only "
            f"{len(substantive)} answer(s) carried usable patient facts"
            + ("; a question was repeated" if repeated else "")
            + ".",
            questions,
        )
    return (
        1,
        f"Interview ran {len(transcript)} turns without gathering a single "
        "substantive patient fact.",
        questions,
    )


def _routing_from_transcript(
    question_interview: dict[str, Any],
) -> tuple[list[str], list[str]]:
    from app.aegis_v1.question_agent import classify_transcript_routing

    return classify_transcript_routing(question_interview)


def _offline_judge(
    question_interview: dict[str, Any],
    teacher: TeacherGradingPacket | None,
) -> QuestionJudgeOutput:
    score, reasoning, questions = _grade_transcript(question_interview)
    substantive, gaps = _routing_from_transcript(question_interview)
    additions = extract_playbook_additions(teacher)
    improvement = sanitize_question_agent_improvement(
        None, playbook_additions=additions
    )
    return QuestionJudgeOutput(
        result=JudgeResult(
            dimension="question_agent",
            reasoning=reasoning,
            score=score,
            confidence=0.8,
            evidence_quotes=questions[:3],
            improvement=improvement,
        ),
        playbook_additions=additions,
        graded=True,
        substantive_questions=substantive,
        gap_questions=gaps,
    )


def _build_judge_prompt(
    question_interview: dict[str, Any],
    teacher: TeacherGradingPacket | None,
) -> str:
    transcript = json.dumps(question_interview.get("qa_transcript") or [], default=str)
    planned = json.dumps(question_interview.get("planned_questions") or [], default=str)
    teacher_context = teacher.clinical_context if teacher else "(none)"
    slice_key = _slice_key(teacher) if teacher else "unknown"
    return f"""You are the QUESTION-AGENT JUDGE for an insurance-appeal training system.
You sit on the teacher side and may see the hidden answer key.

JOB 1 — GRADE THE INTERVIEW (anchor 1, 3, or 5):
Rate the whole transcript. 5 = the agent asked the right patient-knowable
questions, made a best effort to get the relevant answers, no repeats or
wasted turns, never asked the patient a regulatory/policy/legal question.
3 = partial value. 1 = no useful facts, or it asked the patient a regulatory
question (firewall breach — automatic 1).

JOB 1b — CLASSIFY EACH ASKED QUESTION (for GEPA; not shown to the patient):
From the transcript only, list which asked questions yielded substantive
patient facts (`substantive_questions`) vs unresolved gaps (`gap_questions`:
never asked, blank, or "I don't know"). Ignore any pre-existing labels on the
artifact — you are the source of truth.

JOB 2 — MINE PLAYBOOK GAPS (not grading; NOT question-agent mutations):
The synthetic clinical file below embeds regulatory / legal / insurer-specific
facts that a real patient would never know. The question agent must NEVER ask
the patient these — it looks them up via playbook/library. Extract each such
fact and write ONE detailed append-first instruction stating exactly where it
belongs:
- insurer/plan-specific rules -> "Add to playbook:{slice_key}: <rule>"
- broadly applicable legal/regulatory rules -> "Add to global playbook: <rule>"
Only include rules likely missing from standard playbooks. Put these ONLY in
`playbook_additions` — they flow to playbook GEPA reflection, NOT to the
question-agent prompt.

JOB 3 — IMPROVEMENT FIELD (interview technique only):
At most one sentence on patient-knowable interview gaps or technique. NEVER
suggest mutating the question agent to ask regulatory/policy/legal/plan-language
questions of the patient. If the only fix is a regulatory fact, use
`playbook_additions` and leave `improvement` empty.

INTERVIEW TRANSCRIPT:
{transcript}

PLANNED QUESTIONS:
{planned}

SKIPPED: {bool(question_interview.get("skipped"))}

HIDDEN TEACHER CLINICAL FILE (answer key; never shown to the student):
{teacher_context}

Return JSON: score (1|3|5), reasoning, substantive_questions (list of question
strings from the transcript), gap_questions (list of question strings),
playbook_additions (list of instruction strings), improvement (optional one
sentence on patient-knowable interview technique — never regulatory asks)."""


_ANCHOR_CLAMP = {1: 1, 2: 3, 3: 3, 4: 5, 5: 5}


class GeminiQuestionJudgeClient:
    """Vertex/Gemini LLM question judge (live path). Falls back to the
    deterministic offline judge on any failure so a panel never stalls."""

    name = "gemini_question_judge"

    def __init__(self, model: str | None = None, location: str | None = None) -> None:
        self.model = model or os.environ.get(
            "AEGIS_QUESTION_JUDGE_MODEL", "gemini-3.1-pro-preview"
        )
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    def judge(
        self,
        *,
        question_interview: dict[str, Any],
        teacher: TeacherGradingPacket | None,
    ) -> QuestionJudgeOutput:
        try:
            from google import genai
            from google.genai import types

            from app.gemini_retry import generate_content_with_fallback

            class _Out(BaseModel):
                score: int
                reasoning: str = ""
                substantive_questions: list[str] = Field(default_factory=list)
                gap_questions: list[str] = Field(default_factory=list)
                playbook_additions: list[str] = Field(default_factory=list)
                improvement: str = ""

            client = genai.Client(vertexai=True, location=self.location)
            response = generate_content_with_fallback(
                client.models.generate_content,
                model=self.model,
                contents=_build_judge_prompt(question_interview, teacher),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_Out,
                    temperature=0.2,
                ),
            )
            data = _Out.model_validate(json.loads(response.text))
            transcript = list(question_interview.get("qa_transcript") or [])
            questions = [str(t.get("question", "")) for t in transcript]
            regulatory = [q for q in questions if is_regulatory_question(q)]
            score = _ANCHOR_CLAMP.get(int(data.score), 3)
            reasoning = data.reasoning.strip() or "LLM question judge verdict."
            if regulatory:
                score = 1
                reasoning = (
                    "Firewall breach: the agent asked the patient a regulatory/policy "
                    f"question ({regulatory[0]!r}). Regulatory gaps must be looked up "
                    "via playbook/library/Phoenix, never asked of the patient."
                )
            additions = [a.strip() for a in data.playbook_additions if a.strip()]
            additions = additions[:MAX_PLAYBOOK_ADDITIONS]
            improvement = sanitize_question_agent_improvement(
                data.improvement.strip() or None,
                playbook_additions=additions,
            )
            substantive, gaps = _routing_from_transcript(question_interview)
            if data.substantive_questions or data.gap_questions:
                substantive = [q.strip() for q in data.substantive_questions if q.strip()]
                gaps = [q.strip() for q in data.gap_questions if q.strip()]
            return QuestionJudgeOutput(
                result=JudgeResult(
                    dimension="question_agent",
                    reasoning=reasoning,
                    score=score,
                    confidence=0.85,
                    evidence_quotes=[],
                    improvement=improvement,
                ),
                playbook_additions=additions,
                graded=True,
                substantive_questions=substantive,
                gap_questions=gaps,
            )
        except Exception:
            logger.warning(
                "GeminiQuestionJudgeClient failed; falling back to offline judge",
                exc_info=True,
            )
            return _offline_judge(question_interview, teacher)


def judge_question_interview(
    question_interview: dict[str, Any] | None,
    *,
    teacher: TeacherGradingPacket | None = None,
    use_llm: bool = False,
) -> QuestionJudgeOutput:
    """Judge one pre-draft interview artifact (showcase), or return the neutral
    default when none exists (appeal flow — traced, not graded)."""
    if not question_interview:
        return QuestionJudgeOutput(
            result=_neutral_result(
                "No pre-draft interview artifact on this run (appeal flow or "
                "interview disabled). Appeal Q&A is traced, not graded; "
                "neutral default applied."
            ),
            playbook_additions=[],
            graded=False,
        )
    if use_llm:
        return GeminiQuestionJudgeClient().judge(
            question_interview=question_interview, teacher=teacher
        )
    return _offline_judge(question_interview, teacher)
