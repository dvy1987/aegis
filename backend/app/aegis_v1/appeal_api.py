from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from app.aegis_v1.appeal_orchestrator import run_appeal_with_outcome
from app.aegis_v1.patient_context import compose_interactive_clinical_context, normalize_gender
from app.aegis_v1.question_session import QuestionSession, get_question_session_store
from app.aegis_v1.v1_config import build_v1_library_stack

router = APIRouter(prefix="/v1", tags=["appeal"])


class AppealRequest(BaseModel):
    denial_text: str
    case_id: str = "interactive_case"
    insurer: str
    patient_age: int = Field(ge=1, le=120)
    patient_gender: str
    clinical_context: str = ""
    discovery_enabled: bool = False
    # Optional finished pre-draft interview (questions step). Its enriched
    # patient-knowable context replaces clinical_context for drafting.
    interview_id: str | None = None

    @field_validator("insurer")
    @classmethod
    def _validate_insurer(cls, value: str) -> str:
        allowed = {"Aetna", "Cigna", "UHC"}
        if value not in allowed:
            raise ValueError(f"insurer must be one of {sorted(allowed)}")
        return value

    @field_validator("patient_gender")
    @classmethod
    def _validate_gender(cls, value: str) -> str:
        normalized = normalize_gender(value)
        if normalized not in {"F", "M", "X"}:
            raise ValueError("patient_gender must be F, M, or X")
        return normalized


class AppealResponse(BaseModel):
    run_id: str
    appeal_letter: str
    outcome: dict[str, Any]
    risk_flags: list[str]
    trace_metadata: dict[str, Any]
    # Appeal Q&A is traced (and surfaced on the draft page), never graded.
    question_interview: dict[str, Any] | None = None


class QuestionStartRequest(BaseModel):
    denial_text: str
    clinical_context: str = ""
    # Insurer only — the denial type is NOT knowable a priori on appeal, so the
    # question agent gets the complete insurer playbook bundle.
    insurer: str | None = None


class QuestionAnswerRequest(BaseModel):
    answer: str = ""


class QuestionTurnResponse(BaseModel):
    interview_id: str
    question: str | None = None
    turn: int = 0
    done: bool = False
    planned_questions: list[str] = Field(default_factory=list)
    patient_gap_note: str = ""


def get_drafter_client():
    """Offline pipeline stub for tests only.

    Production drafting runs through the ADK ``LlmAgent`` inside the student
    Workflow (Vertex via ``make_retry_model()``). Return ``None`` here; override
  with ``StubDrafterClient`` in unit tests for offline HTTP checks.
    """
    return None


def get_simulator_client():
    """Production Outcome Simulator (ADK LlmAgent). Overridden with a stub in tests."""
    from app.aegis_v1.simulator_client import AdkSimulatorClient

    return AdkSimulatorClient()


def get_question_agent_client():
    """Production question agent resolves to Gemini inside the session store.
    Return ``None`` here; override with ``StubQuestionAgentClient`` in tests."""
    return None


def _turn_response(session: QuestionSession) -> QuestionTurnResponse:
    if session.done:
        result = session.result
        assert result is not None
        return QuestionTurnResponse(
            interview_id=session.interview_id,
            question=None,
            turn=len(session.transcript),
            done=True,
            planned_questions=result.planned_questions,
            patient_gap_note=result.patient_gap_note,
        )
    return QuestionTurnResponse(
        interview_id=session.interview_id,
        question=session.pending_question,
        turn=len(session.transcript) + 1,
        done=False,
    )


@router.post("/appeal/questions/start", response_model=QuestionTurnResponse)
def start_question_interview(
    req: QuestionStartRequest,
    question_agent_client=Depends(get_question_agent_client),
) -> QuestionTurnResponse:
    """Open the turn-based pre-draft interview (appeal flow: traced, not graded).

    The session preps from the complete insurer playbook bundle, Phoenix
    memory, and the local library — never a denial-type-filtered playbook.
    """
    session = get_question_session_store().start(
        denial_text=req.denial_text,
        notes=req.clinical_context,
        insurer=req.insurer or "",
        client=question_agent_client,
    )
    return _turn_response(session)


@router.post("/appeal/questions/{interview_id}/answer", response_model=QuestionTurnResponse)
def answer_question(interview_id: str, req: QuestionAnswerRequest) -> QuestionTurnResponse:
    """Record one patient answer; returns the next question or the finished state."""
    try:
        session = get_question_session_store().answer(interview_id, req.answer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown interview_id")
    return _turn_response(session)


@router.post("/appeal/questions/{interview_id}/skip", response_model=QuestionTurnResponse)
def skip_question_interview(interview_id: str) -> QuestionTurnResponse:
    """Skip the rest of the interview; planned questions become the draft-page gap note."""
    try:
        session = get_question_session_store().skip(interview_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown interview_id")
    return _turn_response(session)


@router.post("/appeal", response_model=AppealResponse)
def create_appeal(
    req: AppealRequest,
    drafter_client=Depends(get_drafter_client),
    simulator_client=Depends(get_simulator_client),
) -> AppealResponse:
    """Draft an appeal and return it together with the insurer Outcome Simulator
    verdict — the artifact the UX shows per appeal run."""
    library_stack = build_v1_library_stack(discovery_enabled=req.discovery_enabled)
    if req.discovery_enabled and not library_stack.get("uses_vertex_store"):
        raise HTTPException(
            status_code=503,
            detail=(
                "Discovery requested but the cloud library is unavailable. "
                "Configure Vertex AI Search (VERTEX_SEARCH_* env vars + credentials) "
                "and try again, or rerun with discovery_enabled=false."
            ),
        )
    question_interview: dict[str, Any] | None = None
    interview_artifact: dict[str, Any] | None = None
    clinical_notes = req.clinical_context
    if req.interview_id:
        try:
            interview_result = get_question_session_store().result(req.interview_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown interview_id")
        if interview_result is None:
            raise HTTPException(
                status_code=409,
                detail="Interview still in progress; answer or skip the remaining questions first.",
            )
        if interview_result.enriched_context:
            # Enriched context = user notes + substantive Q&A answers.
            clinical_notes = interview_result.enriched_context
        # Full artifact rides the workflow/trace (traced, not graded); the
        # consumer response drops internal-only analysis + the raw context blob.
        interview_artifact = interview_result.model_dump()
        question_interview = interview_result.model_dump(
            exclude={"internal_gap_analysis", "enriched_context"}
        )
    clinical_context = compose_interactive_clinical_context(
        patient_age=req.patient_age,
        patient_gender=req.patient_gender,
        clinical_notes=clinical_notes,
    )
    result = run_appeal_with_outcome(
        denial_text=req.denial_text,
        clinical_context=clinical_context,
        case_id=req.case_id,
        insurer=req.insurer,
        patient_age=req.patient_age,
        patient_gender=req.patient_gender,
        drafter_client=drafter_client,
        simulator_client=simulator_client,
        library_stack=library_stack,
        question_interview=interview_artifact,
    )
    pkg = result.appeal_package
    return AppealResponse(
        run_id=pkg["run_id"],
        appeal_letter=pkg["appeal_package_draft"]["appeal_letter"],
        outcome=result.outcome,
        risk_flags=pkg["risk_flags"],
        trace_metadata=pkg["trace_metadata"],
        question_interview=question_interview,
    )
