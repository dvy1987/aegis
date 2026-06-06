from __future__ import annotations

from pathlib import Path

import pytest

from app.aegis_v1.showcase_session import ShowcaseSessionManager, SessionLockedError


def test_start_quick_creates_persisted_diagnostic_session(tmp_path: Path) -> None:
    manager = ShowcaseSessionManager(ledger_dir=tmp_path)

    session = manager.start_quick()

    assert session.session_id.startswith("quick_")
    assert session.run_type == "quick"
    assert session.status == "queued"
    assert session.diagnostics.stage == "queued"
    assert (tmp_path / f"{session.session_id}.json").exists()


def test_serious_is_locked_until_quick_success(tmp_path: Path) -> None:
    manager = ShowcaseSessionManager(ledger_dir=tmp_path)

    with pytest.raises(SessionLockedError):
        manager.start_serious()

    quick = manager.start_quick()
    manager.mark_success(quick.session_id)

    serious = manager.start_serious()
    assert serious.run_type == "serious"


def test_stage_failure_is_persisted_with_retryability(tmp_path: Path) -> None:
    manager = ShowcaseSessionManager(ledger_dir=tmp_path)
    session = manager.start_quick()

    failed = manager.fail_stage(
        session.session_id,
        stage="train_gepa",
        code="timeout",
        message="Backend did not respond during training.",
        retryable=True,
    )
    reloaded = manager.get(session.session_id)

    assert failed.status == "failed"
    assert reloaded.diagnostics.stage == "failed"
    assert reloaded.diagnostics.last_error is not None
    assert reloaded.diagnostics.last_error.code == "timeout"
    assert reloaded.diagnostics.retryable is True


def test_reject_marks_session_without_discarding_proposal(tmp_path: Path) -> None:
    manager = ShowcaseSessionManager(ledger_dir=tmp_path)
    session = manager.start_quick()
    manager.mark_needs_approval(session.session_id, proposal={"candidate_id": "c1"})

    rejected = manager.mark_rejected(session.session_id, reviewer="pm")
    reloaded = manager.get(session.session_id)

    assert rejected.status == "rejected"
    assert rejected.approved_by is None
    assert reloaded.proposal == {"candidate_id": "c1"}
    assert reloaded.diagnostics.stage == "waiting_for_approval"
