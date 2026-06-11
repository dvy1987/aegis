from __future__ import annotations

from pathlib import Path

from app.aegis_v1.showcase_demo_state import MeasuredLiftStore, build_demo_state
from app.aegis_v1.showcase_session import ShowcaseSessionManager


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


def test_demo_state_returns_latest_successful_sessions(tmp_path: Path) -> None:
    manager = ShowcaseSessionManager(ledger_dir=tmp_path)
    quick_old = manager.start_quick(case_ids=["case_1"])
    manager.mark_success(quick_old.session_id)
    quick_new = manager.start_quick(case_ids=["case_2"])
    manager.mark_success(quick_new.session_id)

    state = build_demo_state(manager=manager)
    assert state.preview_session is not None
    assert state.preview_session.session_id == quick_new.session_id
    assert state.production_session is None


def test_demo_state_ignores_failed_sessions(tmp_path: Path) -> None:
    manager = ShowcaseSessionManager(ledger_dir=tmp_path)
    quick = manager.start_quick(case_ids=["case_1"])
    manager.fail_stage(quick.session_id, stage="train_gepa", code="x", message="boom", retryable=False)

    state = build_demo_state(manager=manager)
    assert state.preview_session is None
