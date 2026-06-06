from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


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


def default_ledger_dir() -> Path:
    return Path(os.environ.get("AEGIS_SHOWCASE_LEDGER_DIR", "/tmp/aegis_showcase_sessions"))


class StageError(BaseModel):
    code: str
    message: str


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
    pre_measure_results: list[dict] = Field(default_factory=list)
    training_pre_measure_results: list[dict] = Field(default_factory=list)
    training_post_measure_results: list[dict] = Field(default_factory=list)
    post_measure_results: list[dict] = Field(default_factory=list)


class ShowcaseSessionManager:
    def __init__(self, *, ledger_dir: Path | None = None) -> None:
        self.ledger_dir = ledger_dir or default_ledger_dir()
        self.ledger_dir.mkdir(parents=True, exist_ok=True)

    def start_quick(self, *, case_ids: list[str] | None = None) -> ShowcaseSession:
        return self._create("quick", case_ids or [])

    def start_serious(self, *, case_ids: list[str] | None = None) -> ShowcaseSession:
        if not self._has_successful_quick():
            raise SessionLockedError("serious run is locked until quick run succeeds")
        return self._create("serious", case_ids or [])

    def get(self, session_id: str) -> ShowcaseSession:
        path = self._path(session_id)
        if not path.exists():
            raise FileNotFoundError(session_id)
        return ShowcaseSession.model_validate_json(path.read_text(encoding="utf-8"))

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

    def mark_needs_approval(self, session_id: str, *, proposal: dict | None) -> ShowcaseSession:
        session = self.get(session_id)
        session.status = "needs_approval"
        session.updated_at = _now()
        session.proposal = proposal
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
        self._path(session.session_id).write_text(
            json.dumps(session.model_dump(), indent=2),
            encoding="utf-8",
        )
        return session

    def _path(self, session_id: str) -> Path:
        return self.ledger_dir / f"{session_id}.json"

    def _has_successful_quick(self) -> bool:
        for path in self.ledger_dir.glob("quick_*.json"):
            try:
                session = ShowcaseSession.model_validate_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if session.status == "successful":
                return True
        return False


def cloud_log_filter(session_id: str) -> str:
    return (
        'resource.type="cloud_run_revision" '
        'AND resource.labels.service_name="aegis-v1-api" '
        f'AND jsonPayload.session_id="{session_id}"'
    )
