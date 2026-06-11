from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.aegis_v1.showcase_ledger import (
    LedgerStore,
    default_ledger_dir,
    open_ledger_store,
)


StageName = Literal[
    "queued",
    "measure_before",
    "train_gepa",
    "waiting_for_approval",
    "promote",
    "measure_after",
    "failed",
    "cancelled",
    "rejected",
    "rolled_back",
]
RunStatus = Literal[
    "queued",
    "running",
    "needs_approval",
    "promoted",
    "successful",
    "failed",
    "cancelled",
    "rejected",
    "rolled_back",
]


class SessionLockedError(RuntimeError):
    pass


class SessionBusyError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StageError(BaseModel):
    code: str
    message: str


class CaseFailure(BaseModel):
    case_id: str
    phase: str
    error: str


class ShowcaseCheckpoint(BaseModel):
    """Tracks completed work so a failed run can resume instead of restarting."""

    pre_measure_done: bool = False
    training_pre_done: bool = False
    training_signal_done: bool = False
    training_checkpoint_a_done: bool = False
    optimize_done: bool = False
    train_gepa_candidate_done: bool = False
    training_checkpoint_b_done: bool = False
    training_post_done: bool = False
    promotion_done: bool = False
    post_measure_done: bool = False
    training_trace_ids: list[str] = Field(default_factory=list)
    training_completed_case_ids: list[str] = Field(default_factory=list)
    train_gepa_candidate_completed_case_ids: list[str] = Field(default_factory=list)
    train_gepa_candidate_trace_ids: list[str] = Field(default_factory=list)
    failed_cases: list[CaseFailure] = Field(default_factory=list)


class RunDiagnostics(BaseModel):
    stage: StageName = "queued"
    stage_started_at: str | None = None
    stage_finished_at: str | None = None
    current_case_id: str | None = None
    completed_cases: int = 0
    total_cases: int = 0
    retryable: bool = False
    last_error: StageError | None = None
    phoenix_trace_ids: list[str] = Field(default_factory=list)
    cloud_log_filter: str = ""


class ShowcaseSession(BaseModel):
    session_id: str
    run_type: Literal["quick", "serious"]
    status: RunStatus = "queued"
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    case_ids: list[str] = Field(default_factory=list)
    diagnostics: RunDiagnostics = Field(default_factory=RunDiagnostics)
    cancelled: bool = False
    approved_by: str | None = None
    proposal: dict | None = None
    promotion_preview: dict | None = None
    pre_measure_results: list[dict] = Field(default_factory=list)
    training_pre_measure_results: list[dict] = Field(default_factory=list)
    training_post_measure_results: list[dict] = Field(default_factory=list)
    post_measure_results: list[dict] = Field(default_factory=list)
    regression_detected: bool = False
    regression_summary: str | None = None
    checkpoint: ShowcaseCheckpoint = Field(default_factory=ShowcaseCheckpoint)


class ShowcaseSessionManager:
    def __init__(self, *, ledger_dir: Path | None = None, store: LedgerStore | None = None) -> None:
        self.ledger_dir = ledger_dir or default_ledger_dir()
        self.store = store or open_ledger_store(ledger_dir=self.ledger_dir)
        self.store.ensure_ready()

    def start_quick(self, *, case_ids: list[str] | None = None) -> ShowcaseSession:
        return self._create("quick", case_ids or [])

    def start_serious(self, *, case_ids: list[str] | None = None) -> ShowcaseSession:
        if not self._has_successful_quick():
            raise SessionLockedError("serious run is locked until quick run succeeds")
        return self._create("serious", case_ids or [])

    def get(self, session_id: str) -> ShowcaseSession:
        key = self._key(session_id)
        if not self.store.exists(key):
            raise FileNotFoundError(session_id)
        return ShowcaseSession.model_validate_json(self.store.read_text(key))

    def set_stage(
        self,
        session_id: str,
        *,
        stage: StageName,
        status: RunStatus = "running",
        current_case_id: str | None = None,
        completed_cases: int | None = None,
        total_cases: int | None = None,
    ) -> ShowcaseSession:
        session = self.get(session_id)
        session.status = status
        session.updated_at = _now()
        session.diagnostics.stage = stage
        session.diagnostics.stage_started_at = _now()
        session.diagnostics.stage_finished_at = None
        session.diagnostics.current_case_id = current_case_id
        if completed_cases is not None:
            session.diagnostics.completed_cases = completed_cases
        if total_cases is not None:
            session.diagnostics.total_cases = total_cases
        session.diagnostics.retryable = False
        session.diagnostics.last_error = None
        return self._save(session)

    def fail_stage(
        self,
        session_id: str,
        *,
        stage: str,
        code: str,
        message: str,
        retryable: bool,
    ) -> ShowcaseSession:
        session = self.get(session_id)
        session.status = "failed"
        session.updated_at = _now()
        session.diagnostics.stage = "failed"
        session.diagnostics.stage_finished_at = _now()
        session.diagnostics.retryable = retryable
        session.diagnostics.last_error = StageError(code=code, message=message)
        session.diagnostics.cloud_log_filter = cloud_log_filter(session_id)
        return self._save(session)

    def mark_success(self, session_id: str) -> ShowcaseSession:
        session = self.get(session_id)
        session.status = "successful"
        session.updated_at = _now()
        session.diagnostics.stage_finished_at = _now()
        return self._save(session)

    def mark_needs_approval(
        self,
        session_id: str,
        *,
        proposal: dict | None,
        promotion_preview: dict | None = None,
    ) -> ShowcaseSession:
        session = self.get(session_id)
        session.status = "needs_approval"
        session.updated_at = _now()
        session.proposal = proposal
        session.promotion_preview = promotion_preview
        session.diagnostics.stage = "waiting_for_approval"
        session.diagnostics.stage_finished_at = _now()
        session.diagnostics.retryable = False
        return self._save(session)

    def mark_rejected(self, session_id: str, *, reviewer: str) -> ShowcaseSession:
        session = self.get(session_id)
        session.status = "rejected"
        session.approved_by = None
        session.updated_at = _now()
        session.diagnostics.stage = "waiting_for_approval"
        session.diagnostics.stage_finished_at = _now()
        session.diagnostics.retryable = False
        return self._save(session)

    def measure_results_for(
        self,
        session: ShowcaseSession,
        phase: Literal["pre", "training_pre", "training_post", "post"],
    ) -> list[dict]:
        if phase == "pre":
            return list(session.pre_measure_results)
        if phase == "training_pre":
            return list(session.training_pre_measure_results)
        if phase == "training_post":
            return list(session.training_post_measure_results)
        return list(session.post_measure_results)

    def set_measure_results(
        self,
        session_id: str,
        *,
        phase: Literal["pre", "training_pre", "training_post", "post"],
        results: list[dict],
    ) -> ShowcaseSession:
        session = self.get(session_id)
        if phase == "pre":
            session.pre_measure_results = results
        elif phase == "training_pre":
            session.training_pre_measure_results = results
        elif phase == "training_post":
            session.training_post_measure_results = results
        else:
            session.post_measure_results = results
        session.updated_at = _now()
        return self._save(session)

    def set_regression_warning(self, session_id: str, *, summary: str | None) -> ShowcaseSession:
        session = self.get(session_id)
        session.regression_detected = bool(summary)
        session.regression_summary = summary
        session.updated_at = _now()
        return self._save(session)

    def record_case_failure(
        self,
        session_id: str,
        *,
        phase: str,
        case_id: str,
        error: str,
    ) -> ShowcaseSession:
        session = self.get(session_id)
        session.checkpoint.failed_cases.append(
            CaseFailure(case_id=case_id, phase=phase, error=error)
        )
        session.updated_at = _now()
        return self._save(session)

    def save_checkpoint(self, session_id: str, **updates) -> ShowcaseSession:
        session = self.get(session_id)
        for key, value in updates.items():
            setattr(session.checkpoint, key, value)
        session.updated_at = _now()
        return self._save(session)

    def set_proposal(self, session_id: str, *, proposal: dict | None) -> ShowcaseSession:
        """Persist the GEPA proposal without changing run status, so a resumed
        run can reuse it instead of re-running the optimizer."""
        session = self.get(session_id)
        session.proposal = proposal
        session.updated_at = _now()
        return self._save(session)

    def mark_resumable(self, session_id: str) -> ShowcaseSession:
        """Reset a failed retryable session to running so resume can continue."""
        session = self.get(session_id)
        if session.status != "failed" or not session.diagnostics.retryable:
            raise SessionBusyError("session is not in a retryable failed state")
        session.status = "running"
        session.updated_at = _now()
        session.diagnostics.stage_finished_at = None
        session.diagnostics.last_error = None
        return self._save(session)

    def cancel(self, session_id: str) -> ShowcaseSession:
        session = self.get(session_id)
        session.cancelled = True
        session.status = "cancelled"
        session.updated_at = _now()
        session.diagnostics.stage = "cancelled"
        session.diagnostics.stage_finished_at = _now()
        return self._save(session)

    def _create(self, run_type: Literal["quick", "serious"], case_ids: list[str]) -> ShowcaseSession:
        session_id = f"{run_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        session = ShowcaseSession(
            session_id=session_id,
            run_type=run_type,
            case_ids=case_ids,
            diagnostics=RunDiagnostics(
                stage="queued",
                stage_started_at=_now(),
                total_cases=len(case_ids),
                cloud_log_filter=cloud_log_filter(session_id),
            ),
        )
        return self._save(session)

    def _save(self, session: ShowcaseSession) -> ShowcaseSession:
        self.store.write_text(
            self._key(session.session_id),
            json.dumps(session.model_dump(), indent=2),
        )
        return session

    def _key(self, session_id: str) -> str:
        return f"{session_id}.json"

    def _path(self, session_id: str) -> Path:
        """Local filesystem path (tests / legacy); prefer ``store`` in production."""
        return self.ledger_dir / self._key(session_id)

    def list_sessions(self, *, run_type: Literal["quick", "serious"] | None = None) -> list[ShowcaseSession]:
        prefix = f"{run_type}_" if run_type else ""
        sessions: list[ShowcaseSession] = []
        for key in self.store.list_keys(prefix):
            if not key.endswith(".json") or key in {"promotion_stack.json", "measured_lift.json"}:
                continue
            try:
                sessions.append(ShowcaseSession.model_validate_json(self.store.read_text(key)))
            except Exception:
                continue
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    def latest_session(
        self,
        run_type: Literal["quick", "serious"],
        *,
        statuses: frozenset[str] | None = None,
    ) -> ShowcaseSession | None:
        allowed = statuses or frozenset({"successful"})
        for session in self.list_sessions(run_type=run_type):
            if session.status in allowed:
                return session
        return None

    def _has_successful_quick(self) -> bool:
        return self.latest_session("quick") is not None


def cloud_log_filter(session_id: str) -> str:
    return (
        'resource.type="cloud_run_revision" '
        'AND resource.labels.service_name="aegis-v1-api" '
        f'AND jsonPayload.session_id="{session_id}"'
    )
