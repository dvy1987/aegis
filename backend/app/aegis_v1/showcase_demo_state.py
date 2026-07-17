"""Durable hackathon demo assets — measured lift + latest successful runs."""
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.aegis_v1.showcase_ledger import LedgerStore, open_ledger_store
from app.aegis_v1.showcase_run_policy import showcase_runs_enabled
from app.aegis_v1.showcase_session import ShowcaseSession, ShowcaseSessionManager

MEASURED_LIFT_KEY = "measured_lift.json"
RESTORABLE_RUN_STATUSES = frozenset({"successful"})


def _matrix_score(session: ShowcaseSession) -> int:
    """More scored cases → better demo restore (ignores empty successful shells)."""
    return (
        len(session.pre_measure_results)
        + len(session.training_pre_measure_results)
        + len(session.training_post_measure_results)
        + len(session.post_measure_results)
    )


def _latest_demo_session(
    manager: ShowcaseSessionManager,
    run_type: Literal["quick", "serious"],
) -> ShowcaseSession | None:
    """Pick the successful run with the richest measurement grid (ties → newest)."""
    best: ShowcaseSession | None = None
    best_score = 0
    for session in manager.list_sessions(run_type=run_type):
        if session.status not in RESTORABLE_RUN_STATUSES:
            continue
        score = _matrix_score(session)
        if score > best_score:
            best_score = score
            best = session
    return best


class MeasuredLiftCase(BaseModel):
    baseline: dict[str, Any] | None = None
    candidate: dict[str, Any] | None = None


class ShowcaseDemoState(BaseModel):
    preview_session: ShowcaseSession | None = None
    production_session: ShowcaseSession | None = None
    measured_lift: dict[str, MeasuredLiftCase] = Field(default_factory=dict)
    runs_enabled: bool = True


class MeasuredLiftStore:
    def __init__(self, store: LedgerStore | None = None) -> None:
        self.store = store or open_ledger_store()
        self.store.ensure_ready()

    def read_all(self) -> dict[str, dict[str, dict[str, Any]]]:
        if not self.store.exists(MEASURED_LIFT_KEY):
            return {}
        return json.loads(self.store.read_text(MEASURED_LIFT_KEY))

    def save_variant(self, case_id: str, variant: Literal["baseline", "candidate"], result: dict[str, Any]) -> None:
        data = self.read_all()
        entry = data.setdefault(case_id, {})
        entry[variant] = result
        self.store.write_text(MEASURED_LIFT_KEY, json.dumps(data, indent=2))


def build_demo_state(*, manager: ShowcaseSessionManager | None = None) -> ShowcaseDemoState:
    sessions = manager or ShowcaseSessionManager()
    lift_store = MeasuredLiftStore(store=sessions.store)
    raw_lift = lift_store.read_all()
    measured_lift = {
        case_id: MeasuredLiftCase(
            baseline=entry.get("baseline"),
            candidate=entry.get("candidate"),
        )
        for case_id, entry in raw_lift.items()
    }
    return ShowcaseDemoState(
        preview_session=_latest_demo_session(sessions, "quick"),
        production_session=_latest_demo_session(sessions, "serious"),
        measured_lift=measured_lift,
        runs_enabled=showcase_runs_enabled(),
    )
