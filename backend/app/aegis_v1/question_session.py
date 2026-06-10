"""Turn-based pre-draft interview sessions for the /appeal API (Phase 2).

On showcase the interview runs in-process against the patient simulator
(`question_workflow.run_pre_draft_interview`). On `/appeal` the responder is a
real person on the other side of HTTP, so the interview is held open as a
session: `start` returns the first question, each `answer` returns the next
one (or finalizes), and `skip` finalizes immediately with the planned
questions for the draft-page gap note.

Appeal interviews are TRACED, not graded — no answer key exists for a real
user. The finalized ``QuestionInterviewResult`` feeds the drafter's enriched
context and the UX gap note only.

In-memory by design: sessions are short-lived, single-process, and the draft
request follows immediately. Swap the store for Redis/DB if the API goes
multi-worker.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.aegis_v1.question_agent import (
    MAX_QUESTIONS,
    QuestionAgentClient,
    QuestionDecision,
    finalize_interview_result,
)
from app.aegis_v1.schemas import QATurn, QuestionInterviewResult


@dataclass
class QuestionSession:
    interview_id: str
    denial_text: str
    notes: str
    playbook: dict[str, Any]
    client: QuestionAgentClient
    max_questions: int = MAX_QUESTIONS
    transcript: list[QATurn] = field(default_factory=list)
    planned_questions: list[str] = field(default_factory=list)
    pending_question: str = ""
    gap_analysis: str = ""
    phoenix_summary: dict[str, Any] = field(default_factory=dict)
    library_context: str = ""
    result: QuestionInterviewResult | None = None

    @property
    def done(self) -> bool:
        return self.result is not None


class QuestionSessionStore:
    """Thread-safe in-memory store of open interview sessions.

    The step semantics mirror `question_agent.run_question_interview` exactly:
    adaptive next-question decisions, never repeat a question, cap at
    ``max_questions``, and the same finalization (enriched context, gap note).
    """

    def __init__(self) -> None:
        self._sessions: dict[str, QuestionSession] = {}
        self._lock = threading.Lock()

    def _decide(self, session: QuestionSession) -> QuestionDecision:
        return session.client.decide(
            denial_text=session.denial_text,
            notes=session.notes,
            playbook=session.playbook,
            phoenix_summary=session.phoenix_summary,
            transcript=session.transcript,
            library_context=session.library_context,
        )

    def start(
        self,
        *,
        denial_text: str,
        notes: str = "",
        insurer: str = "",
        playbook: dict[str, Any] | None = None,
        client: QuestionAgentClient | None = None,
        max_questions: int = MAX_QUESTIONS,
    ) -> QuestionSession:
        if client is None:
            from app.aegis_v1.question_agent import GeminiQuestionAgentClient

            client = GeminiQuestionAgentClient()
        # Prep (best-effort, mirrors the in-workflow node): the COMPLETE insurer
        # playbook bundle (denial type unknown a priori), Phoenix memory, and a
        # library/corpus lookup — so the agent never asks what a lookup answers.
        if playbook is None and insurer:
            try:
                from app.aegis_v1.geo_playbook import question_agent_prep_bundle

                playbook = question_agent_prep_bundle(insurer)
            except Exception:
                playbook = {}
        phoenix_summary: dict[str, Any] = {}
        if insurer:
            try:
                from app.aegis_v1.tools import phoenix_mcp_lookup

                phoenix_summary = phoenix_mcp_lookup(
                    insurer=insurer, denial_type="unknown"
                )
            except Exception:
                phoenix_summary = {}
        library_context = ""
        try:
            from app.aegis_v1.tools import corpus_retrieval

            retrieval = corpus_retrieval(denial_text[:300])
            library_context = "\n".join(
                f"- {hit.get('title', '')}: {hit.get('quote', '')}"
                for hit in (retrieval.get("hits") or [])
                if isinstance(hit, dict)
            )
        except Exception:
            library_context = ""
        session = QuestionSession(
            interview_id=uuid.uuid4().hex,
            denial_text=denial_text,
            notes=notes,
            playbook=dict(playbook or {}),
            client=client,
            max_questions=max_questions,
            phoenix_summary=phoenix_summary,
            library_context=library_context,
        )
        first = self._decide(session)
        session.planned_questions = list(first.planned_questions)[:max_questions]
        session.gap_analysis = first.gap_analysis
        if first.action == "ask" and first.question:
            session.pending_question = first.question
        else:
            self._finalize(session, skipped=False)
        with self._lock:
            self._sessions[session.interview_id] = session
        return session

    def get(self, interview_id: str) -> QuestionSession:
        """Raises KeyError for unknown ids (API layer maps it to 404)."""
        with self._lock:
            return self._sessions[interview_id]

    def answer(self, interview_id: str, answer: str) -> QuestionSession:
        session = self.get(interview_id)
        if session.done or not session.pending_question:
            return session
        session.transcript.append(
            QATurn(
                turn=len(session.transcript) + 1,
                question=session.pending_question,
                answer=answer or "",
            )
        )
        session.pending_question = ""
        decision = self._decide(session)
        session.gap_analysis = decision.gap_analysis or session.gap_analysis
        asked = {turn.question for turn in session.transcript}
        if (
            decision.action == "ask"
            and decision.question
            and decision.question not in asked  # never repeat a question
            and len(session.transcript) < session.max_questions
        ):
            session.pending_question = decision.question
        else:
            self._finalize(session, skipped=False)
        return session

    def skip(self, interview_id: str) -> QuestionSession:
        session = self.get(interview_id)
        if not session.done:
            session.pending_question = ""
            self._finalize(session, skipped=True)
        return session

    def result(self, interview_id: str) -> QuestionInterviewResult | None:
        """Finalized result, or None while the interview is still in progress."""
        return self.get(interview_id).result

    def _finalize(self, session: QuestionSession, *, skipped: bool) -> None:
        if skipped and not session.transcript:
            session.result = finalize_interview_result(
                notes=session.notes,
                transcript=[],
                planned_questions=session.planned_questions,
                decision=QuestionDecision(
                    action="stop",
                    planned_questions=session.planned_questions,
                    gap_analysis=session.gap_analysis,
                ),
                skipped=True,
                gap_analysis=session.gap_analysis,
            )
            return
        decision = self._decide(session)
        session.gap_analysis = decision.gap_analysis or session.gap_analysis
        session.result = finalize_interview_result(
            notes=session.notes,
            transcript=list(session.transcript),
            planned_questions=session.planned_questions,
            decision=decision,
            skipped=skipped,
            gap_analysis=session.gap_analysis,
        )


_STORE = QuestionSessionStore()


def get_question_session_store() -> QuestionSessionStore:
    return _STORE
