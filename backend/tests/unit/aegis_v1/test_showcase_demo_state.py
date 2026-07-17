from __future__ import annotations

from pathlib import Path

from app.aegis_v1.showcase_demo_state import MeasuredLiftStore, build_demo_state
from app.aegis_v1.showcase_ledger import LocalLedgerStore
from app.aegis_v1.showcase_session import ShowcaseSessionManager


def _manager(tmp_path: Path) -> ShowcaseSessionManager:
    return ShowcaseSessionManager(store=LocalLedgerStore(tmp_path))


def test_measured_lift_persists_per_case_and_variant(tmp_path: Path) -> None:
    store = MeasuredLiftStore(store=__import__("app.aegis_v1.showcase_ledger", fromlist=["LocalLedgerStore"]).LocalLedgerStore(tmp_path))
    payload = {
        "case_id": "case_168_aetna_priorauth",
        "variant": "baseline",
        "verdict": "DENY",
        "score": 0.2,
        "threshold": 0.7,
        "letter_excerpt": "excerpt",
        "appeal_letter": "letter",
        "outcome": {"verdict": "DENY", "score": 0.2, "threshold": 0.7, "feature_scores": [], "gaps": [], "critique": "", "rationale": []},
        "prompt_version": "drafter_v1",
        "risk_flags": [],
    }
    store.save_variant("case_168_aetna_priorauth", "baseline", payload)
    store.save_variant("case_168_aetna_priorauth", "candidate", {**payload, "variant": "candidate", "score": 0.8, "verdict": "APPROVE"})

    data = store.read_all()
    assert data["case_168_aetna_priorauth"]["baseline"]["score"] == 0.2
    assert data["case_168_aetna_priorauth"]["candidate"]["score"] == 0.8


def test_demo_state_prefers_richest_successful_run(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    rich = manager.start_quick(case_ids=["case_1"])
    rich.pre_measure_results = [{"case_id": "case_1", "verdict": "DENY"}]
    rich.training_pre_measure_results = [
        {"case_id": "case_2", "verdict": "APPROVE"},
        {"case_id": "case_3", "verdict": "DENY"},
    ]
    manager._save(rich)
    manager.mark_success(rich.session_id)

    sparse_newer = manager.start_quick(case_ids=["case_9"])
    sparse_newer.pre_measure_results = [{"case_id": "case_9", "verdict": "DENY"}]
    manager._save(sparse_newer)
    manager.mark_success(sparse_newer.session_id)

    state = build_demo_state(manager=manager)
    assert state.preview_session is not None
    assert state.preview_session.session_id == rich.session_id
    assert len(state.preview_session.training_pre_measure_results) == 2


def test_demo_state_returns_none_when_no_scored_success(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    quick = manager.start_quick(case_ids=["case_1"])
    manager.mark_success(quick.session_id)

    state = build_demo_state(manager=manager)
    assert state.preview_session is None


def test_demo_state_ignores_failed_sessions(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    quick = manager.start_quick(case_ids=["case_1"])
    manager.fail_stage(quick.session_id, stage="train_gepa", code="x", message="boom", retryable=False)

    state = build_demo_state(manager=manager)
    assert state.preview_session is None
