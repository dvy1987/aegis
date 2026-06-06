from __future__ import annotations

from pathlib import Path

from app.aegis_v1 import showcase_runner
from app.aegis_v1.showcase_runner import approve_session, run_quick_session, run_serious_session
from app.aegis_v1.showcase_manifest import load_showcase_manifest
from app.aegis_v1.showcase_session import ShowcaseSessionManager
from app.learning.models import Candidate, Component, ExperimentResult, PromotionProposal


def _proposal() -> PromotionProposal:
    candidate = Candidate(
        candidate_id="c1",
        components={
            "drafter_system_prompt": Component(
                component_id="drafter_system_prompt",
                kind="prompt",
                version="drafter_v3",
                text="candidate prompt",
            ),
            "playbook:Cigna:medical_necessity": Component(
                component_id="playbook:Cigna:medical_necessity",
                kind="playbook",
                version="cigna_mednec_v3",
                playbook={"tactics": ["Use the candidate playbook."]},
            )
        },
        origin="reflect",
    )
    return PromotionProposal(
        candidate=candidate,
        before=ExperimentResult(candidate_id="seed", dataset_split="pre", composite=0.2),
        after=ExperimentResult(candidate_id="c1", dataset_split="post", composite=0.8),
        per_dimension_deltas={"grounding": 0.2},
        vetoes=[],
    )


def test_quick_session_uses_holdout_and_training_rows_before_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    calls: list[dict] = []
    optimize_kwargs: dict = {}

    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        calls.append(
            {
                "phase": phase,
                "case_ids": [case.case_id for case in cases],
                "prompt_text": kwargs.get("drafter_prompt_text"),
                "playbook_overrides": kwargs.get("playbook_overrides"),
            }
        )
        manager.set_measure_results(
            session_id,
            phase=phase,
            results=[{"case_id": case.case_id} for case in cases],
        )
        return []

    def fake_optimize(**kwargs):
        optimize_kwargs.update(kwargs)
        return _proposal()

    monkeypatch.setattr(showcase_runner, "_creds_available", lambda: True)
    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)
    monkeypatch.setattr(showcase_runner, "_seed_training_signal", lambda *args, **kwargs: ["trace-1"])
    monkeypatch.setattr(showcase_runner, "_optimize", fake_optimize)

    run_quick_session(session.session_id)

    assert calls[0]["phase"] == "pre"
    assert calls[0]["case_ids"] == ["case_13_cigna_mednec", "case_46_cigna_mednec"]
    assert calls[1]["phase"] == "training_pre"
    assert calls[1]["case_ids"] == [
        "case_01_cigna_mednec",
        "case_07_cigna_mednec",
        "case_19_cigna_mednec",
        "case_22_cigna_mednec",
        "case_30_cigna_mednec",
        "case_35_cigna_mednec",
        "case_45_cigna_mednec",
        "case_48_cigna_mednec",
    ]
    assert calls[2]["phase"] == "training_post"
    assert calls[2]["prompt_text"] == "candidate prompt"
    assert calls[2]["playbook_overrides"]
    assert optimize_kwargs["slice_filters"] == ["Cigna:medical_necessity"]
    assert manager.get(session.session_id).status == "needs_approval"


def test_approve_session_writes_rollback_checkpoint_before_promotion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    manager.mark_needs_approval(session.session_id, proposal=_proposal().model_dump())
    events: list[str] = []
    measure_calls: list[dict] = []

    class FakeStack:
        def push_checkpoint(self, *, run_type, session_id, candidate):
            events.append(f"checkpoint:{run_type}:{session_id}:{candidate.candidate_id}")

    class FakeStore:
        def register_promotion(self, candidate, audit):
            events.append(f"promote:{candidate.candidate_id}:{audit.approver}")

    monkeypatch.setattr(showcase_runner, "PromotionStack", lambda: FakeStack(), raising=False)
    monkeypatch.setattr(showcase_runner, "LivePhoenixLearningStore", lambda: FakeStore())
    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        measure_calls.append({"phase": phase, "case_ids": [case.case_id for case in cases]})
        manager.set_measure_results(
            session_id,
            phase=phase,
            results=[{"case_id": case.case_id} for case in cases],
        )
        return []

    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)

    approve_session(session.session_id, approver="pm")

    assert events == [
        f"checkpoint:quick:{session.session_id}:c1",
        "promote:c1:pm",
    ]
    assert measure_calls == [
        {"phase": "post", "case_ids": ["case_13_cigna_mednec", "case_46_cigna_mednec"]}
    ]
    assert manager.get(session.session_id).status == "successful"


def test_serious_session_uses_serious_train_and_holdout_with_multi_slice(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    quick = manager.start_quick()
    manager.mark_success(quick.session_id)
    session = manager.start_serious()
    calls: list[dict] = []
    optimize_kwargs: dict = {}

    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        calls.append(
            {
                "phase": phase,
                "case_ids": [case.case_id for case in cases],
                "prompt_text": kwargs.get("drafter_prompt_text"),
                "playbook_overrides": kwargs.get("playbook_overrides"),
            }
        )
        manager.set_measure_results(
            session_id,
            phase=phase,
            results=[{"case_id": case.case_id} for case in cases],
        )
        return []

    def fake_optimize(**kwargs):
        optimize_kwargs.update(kwargs)
        return _proposal()

    monkeypatch.setattr(showcase_runner, "_creds_available", lambda: True)
    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)
    monkeypatch.setattr(showcase_runner, "_seed_training_signal", lambda *args, **kwargs: ["trace-1"])
    monkeypatch.setattr(showcase_runner, "_optimize", fake_optimize)

    run_serious_session(session.session_id)

    assert calls[0]["phase"] == "pre"
    assert len(calls[0]["case_ids"]) == 20
    assert calls[1]["phase"] == "training_pre"
    assert len(calls[1]["case_ids"]) == 80
    assert calls[2]["phase"] == "training_post"
    assert len(calls[2]["case_ids"]) == 80
    assert calls[2]["prompt_text"] == "candidate prompt"
    assert set(optimize_kwargs["slice_filters"]) == {
        "Aetna:medical_necessity",
        "Aetna:prior_authorization",
        "Cigna:medical_necessity",
        "Cigna:prior_authorization",
        "UnitedHealthcare:medical_necessity",
        "UnitedHealthcare:prior_authorization",
    }
    assert manager.get(session.session_id).status == "needs_approval"


def test_measure_stops_before_case_work_when_session_cancelled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    manager.cancel(session.session_id)
    called = False

    def fail_measurement(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("cancelled measurement should not run case work")

    monkeypatch.setattr(showcase_runner, "run_measurement_case", fail_measurement)

    results = showcase_runner._measure(
        manager,
        session.session_id,
        phase="pre",
        cases=load_showcase_manifest().quick_holdout,
    )

    assert results == []
    assert called is False


def test_approval_marks_regression_when_holdout_score_drops(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    manager.set_measure_results(
        session.session_id,
        phase="pre",
        results=[
            {"case_id": "case_13_cigna_mednec", "verdict": "APPROVE", "score": 0.9},
            {"case_id": "case_46_cigna_mednec", "verdict": "APPROVE", "score": 0.8},
        ],
    )
    manager.mark_needs_approval(session.session_id, proposal=_proposal().model_dump())

    class FakeStack:
        def push_checkpoint(self, *, run_type, session_id, candidate):
            return None

    class FakeStore:
        def register_promotion(self, candidate, audit):
            return None

    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        results = [
            {"case_id": "case_13_cigna_mednec", "verdict": "DENY", "score": 0.3},
            {"case_id": "case_46_cigna_mednec", "verdict": "APPROVE", "score": 0.75},
        ]
        manager.set_measure_results(session_id, phase=phase, results=results)
        return results

    monkeypatch.setattr(showcase_runner, "PromotionStack", lambda: FakeStack(), raising=False)
    monkeypatch.setattr(showcase_runner, "LivePhoenixLearningStore", lambda: FakeStore())
    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)

    approve_session(session.session_id, approver="pm")

    reloaded = manager.get(session.session_id)
    assert reloaded.regression_detected is True
    assert "consider rolling back" in (reloaded.regression_summary or "")
