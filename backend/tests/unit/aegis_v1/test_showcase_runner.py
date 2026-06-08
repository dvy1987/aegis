from __future__ import annotations

from pathlib import Path

from app.aegis_v1 import showcase_runner
from app.aegis_v1.showcase_manifest import load_showcase_manifest
from app.aegis_v1.showcase_runner import (
    approve_session,
    run_quick_session,
    run_serious_session,
)
from app.aegis_v1.showcase_session import ShowcaseSessionManager
from app.learning.models import (
    Candidate,
    Component,
    ExperimentResult,
    PromotionProposal,
)


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
    # 8 training cases → guard needs 4 successful traces.
    monkeypatch.setattr(
        showcase_runner,
        "_seed_training_signal",
        lambda *args, **kwargs: ["t1", "t2", "t3", "t4"],
    )
    monkeypatch.setattr(showcase_runner, "_optimize", fake_optimize)
    monkeypatch.setattr(showcase_runner, "_write_training_checkpoint", lambda *a, **k: [])
    monkeypatch.setattr(showcase_runner, "_eval_post_gepa_candidate", lambda *a, **k: [])

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


def test_training_signal_gives_teacher_packet_only_to_judges(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    seen_cases: list[dict] = []

    class FakeRecorder:
        pass

    class FakeDrafter:
        pass

    class FakeJudge:
        pass

    def fake_run_evaluated_case(case_obj, **kwargs):
        seen_cases.append(case_obj)

        class Run:
            trace_ref = "trace-1"

        return Run()

    monkeypatch.setattr(showcase_runner, "OtelPhoenixRecorder", FakeRecorder)
    monkeypatch.setattr(showcase_runner, "GeminiJudgeClient", FakeJudge)
    monkeypatch.setattr(showcase_runner, "run_evaluated_case", fake_run_evaluated_case)

    trace_ids = showcase_runner._seed_training_signal(
        manager,
        session.session_id,
        cases=load_showcase_manifest().quick_train[:1],
        dataset_split="train_split",
    )

    assert trace_ids == ["trace-1"]
    assert seen_cases[0]["dataset_split"] == "train_split"
    assert "synthetic_provenance" in seen_cases[0]
    assert "denial_pattern_sources" in seen_cases[0]


def test_optimizer_dataset_keeps_drafter_fields_student_safe_with_private_teacher_case() -> None:
    item = showcase_runner._dataset(load_showcase_manifest().quick_train[:1])[0]
    drafter_payload = {
        "parsed_case": item["parsed_case"],
        "citations": item["citations"],
        "phoenix_summary": item["phoenix_summary"],
        "denial_letter_text": item["denial_letter_text"],
        "clinical_context": item["clinical_context"],
    }
    haystack = str(drafter_payload)

    assert "synthetic_provenance" not in haystack
    assert "denial_pattern_sources" not in haystack
    assert "patient_profile" not in haystack
    assert "synthetic_provenance" in item["_teacher_case"]


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


def test_approve_session_skips_promotion_when_already_promoted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # A resumed approval (promotion already checkpointed) must NOT register the
    # candidate a second time — it should only finish the post-measure.
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    manager.mark_needs_approval(session.session_id, proposal=_proposal().model_dump())
    manager.save_checkpoint(session.session_id, promotion_done=True)
    events: list[str] = []
    measure_calls: list[str] = []

    class FakeStack:
        def push_checkpoint(self, *, run_type, session_id, candidate):
            events.append("checkpoint")

    class FakeStore:
        def register_promotion(self, candidate, audit):
            events.append("promote")

    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        measure_calls.append(phase)
        manager.set_measure_results(session_id, phase=phase, results=[])
        return []

    monkeypatch.setattr(showcase_runner, "PromotionStack", lambda: FakeStack(), raising=False)
    monkeypatch.setattr(showcase_runner, "LivePhoenixLearningStore", lambda: FakeStore())
    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)

    approve_session(session.session_id, approver="pm")

    assert events == []  # promotion not repeated
    assert measure_calls == ["post"]
    reloaded = manager.get(session.session_id)
    assert reloaded.status == "successful"
    assert reloaded.checkpoint.post_measure_done is True


def test_resume_after_promotion_continues_approval_not_learning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    monkeypatch.setenv("AEGIS_SHOWCASE_AUTORUN", "false")
    from app.aegis_v1 import showcase_api

    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    sid = session.session_id
    manager.mark_needs_approval(sid, proposal=_proposal().model_dump())
    manager.save_checkpoint(sid, promotion_done=True)
    promoted = manager.get(sid)
    promoted.approved_by = "pm"
    manager._save(promoted)
    manager.fail_stage(
        sid, stage="promote", code="Timeout", message="boom", retryable=True
    )

    calls: dict[str, object] = {}
    monkeypatch.setattr(
        showcase_api,
        "_launch_approve",
        lambda session_id, approver: calls.update(approve=(session_id, approver)),
    )
    monkeypatch.setattr(
        showcase_api, "_launch_quick", lambda session_id: calls.update(quick=session_id)
    )

    resumed = showcase_api.resume_run(sid)

    assert calls.get("approve") == (sid, "pm")
    assert "quick" not in calls
    assert resumed.status == "running"
    assert resumed.diagnostics.last_error is None


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
    # 80 training cases → guard needs 40 successful traces.
    monkeypatch.setattr(
        showcase_runner,
        "_seed_training_signal",
        lambda *args, **kwargs: [f"t{i}" for i in range(40)],
    )
    monkeypatch.setattr(showcase_runner, "_optimize", fake_optimize)
    monkeypatch.setattr(showcase_runner, "_write_training_checkpoint", lambda *a, **k: [])
    monkeypatch.setattr(showcase_runner, "_eval_post_gepa_candidate", lambda *a, **k: [])

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


def test_insufficient_training_data_blocks_optimize(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    optimize_called = False

    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        manager.set_measure_results(session_id, phase=phase, results=[])
        return []

    def fake_optimize(**kwargs):
        nonlocal optimize_called
        optimize_called = True
        return _proposal()

    monkeypatch.setattr(showcase_runner, "_creds_available", lambda: True)
    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)
    # Quick train has 8 cases → needs 4; only 1 produced a trace.
    monkeypatch.setattr(
        showcase_runner, "_seed_training_signal", lambda *a, **k: ["only-one"]
    )
    monkeypatch.setattr(showcase_runner, "_optimize", fake_optimize)
    monkeypatch.setattr(showcase_runner, "_write_training_checkpoint", lambda *a, **k: [])

    run_quick_session(session.session_id)

    assert optimize_called is False
    reloaded = manager.get(session.session_id)
    assert reloaded.status == "failed"
    err = reloaded.diagnostics.last_error
    assert err is not None and err.code == "insufficient_training_data"
    assert "1 of 8" in err.message
    assert reloaded.diagnostics.retryable is True


def test_sufficient_training_data_allows_optimize(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    optimize_called = False

    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        manager.set_measure_results(session_id, phase=phase, results=[])
        return []

    def fake_optimize(**kwargs):
        nonlocal optimize_called
        optimize_called = True
        return _proposal()

    monkeypatch.setattr(showcase_runner, "_creds_available", lambda: True)
    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)
    # 8 training cases → needs 4; provide 4 traces.
    monkeypatch.setattr(
        showcase_runner, "_seed_training_signal", lambda *a, **k: ["t1", "t2", "t3", "t4"]
    )
    monkeypatch.setattr(showcase_runner, "_optimize", fake_optimize)
    monkeypatch.setattr(showcase_runner, "_write_training_checkpoint", lambda *a, **k: [])
    monkeypatch.setattr(showcase_runner, "_eval_post_gepa_candidate", lambda *a, **k: [])

    run_quick_session(session.session_id)

    assert optimize_called is True
    assert manager.get(session.session_id).status == "needs_approval"


def test_no_learning_signal_uses_plain_english_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()

    monkeypatch.setattr(showcase_runner, "_creds_available", lambda: True)
    monkeypatch.setattr(
        showcase_runner,
        "_measure",
        lambda *a, **k: manager.set_measure_results(
            a[1] if len(a) > 1 else k["session_id"], phase=k["phase"], results=[]
        ),
    )
    # Provide enough traces to clear the minimum-data guard (8 train → needs 4),
    # so the run reaches the no-learning-signal path.
    monkeypatch.setattr(
        showcase_runner, "_seed_training_signal", lambda *a, **k: ["t1", "t2", "t3", "t4"]
    )
    monkeypatch.setattr(showcase_runner, "_optimize", lambda **k: None)
    monkeypatch.setattr(showcase_runner, "_write_training_checkpoint", lambda *a, **k: [])

    run_quick_session(session.session_id)

    reloaded = manager.get(session.session_id)
    assert reloaded.status == "failed"
    err = reloaded.diagnostics.last_error
    assert err is not None and err.code == "no_learning_signal"
    # Plain-English: mentions how many cases were judged, not a bare code.
    assert "4 case" in err.message
    assert reloaded.diagnostics.retryable is True


def test_measure_skips_failing_case_and_continues(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()

    class FakeResult:
        def __init__(self, case_id: str) -> None:
            self._case_id = case_id

        def model_dump(self) -> dict:
            return {"case_id": self._case_id}

    seen: list[str] = []

    def flaky_measure(case_obj, **kwargs):
        case_id = case_obj["case_id"]
        seen.append(case_id)
        if case_id == "case_46_cigna_mednec":
            raise RuntimeError("simulated model error")
        return FakeResult(case_id)

    monkeypatch.setattr(showcase_runner, "AdkSimulatorClient", lambda: object())
    monkeypatch.setattr(showcase_runner, "run_measurement_case", flaky_measure)

    results = showcase_runner._measure(
        manager,
        session.session_id,
        phase="pre",
        cases=load_showcase_manifest().quick_holdout,
    )

    # The good case is kept; the failing case is skipped, not fatal.
    assert {r["case_id"] for r in results} == {"case_13_cigna_mednec"}
    reloaded = manager.get(session.session_id)
    failed_ids = [f.case_id for f in reloaded.checkpoint.failed_cases]
    assert "case_46_cigna_mednec" in failed_ids
    assert len(seen) == 2


def test_training_signal_skips_failing_case_and_continues(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    cases = load_showcase_manifest().quick_train[:3]
    fail_id = cases[1].case_id

    class Run:
        trace_ref = "trace-ok"

    def flaky_eval(case_obj, **kwargs):
        if case_obj["case_id"] == fail_id:
            raise RuntimeError("judge error")
        return Run()

    monkeypatch.setattr(showcase_runner, "OtelPhoenixRecorder", lambda: object())
    monkeypatch.setattr(showcase_runner, "GeminiJudgeClient", lambda: object())
    monkeypatch.setattr(showcase_runner, "run_evaluated_case", flaky_eval)

    trace_ids = showcase_runner._seed_training_signal(
        manager,
        session.session_id,
        cases=cases,
        dataset_split="train_split",
    )

    # Two good cases produce traces; the failing one is recorded and skipped.
    assert trace_ids == ["trace-ok", "trace-ok"]
    reloaded = manager.get(session.session_id)
    failed_ids = [f.case_id for f in reloaded.checkpoint.failed_cases]
    assert failed_ids == [fail_id]


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


def test_resume_skips_completed_stages_and_reuses_proposal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    sid = session.session_id

    # Simulate a run that already completed everything except the final
    # post-training measurement before it was interrupted.
    manager.set_proposal(sid, proposal=_proposal().model_dump())
    manager.save_checkpoint(
        sid,
        pre_measure_done=True,
        training_pre_done=True,
        training_checkpoint_a_done=True,
        training_signal_done=True,
        training_trace_ids=["t1", "t2", "t3", "t4"],
        optimize_done=True,
        train_gepa_candidate_done=True,
        training_checkpoint_b_done=True,
    )

    measure_phases: list[str] = []

    def fake_measure(manager, session_id, *, phase, cases, **kwargs):
        measure_phases.append(phase)
        manager.set_measure_results(session_id, phase=phase, results=[])
        return []

    def boom_seed(*args, **kwargs):
        raise AssertionError("training signal should not re-run on resume")

    def boom_optimize(**kwargs):
        raise AssertionError("optimize should not re-run on resume")

    monkeypatch.setattr(showcase_runner, "_creds_available", lambda: True)
    monkeypatch.setattr(showcase_runner, "_measure", fake_measure)
    monkeypatch.setattr(showcase_runner, "_seed_training_signal", boom_seed)
    monkeypatch.setattr(showcase_runner, "_optimize", boom_optimize)

    run_quick_session(sid)

    # Only the remaining stage (training_post) runs; earlier stages are skipped.
    assert measure_phases == ["training_post"]
    reloaded = manager.get(sid)
    assert reloaded.status == "needs_approval"
    assert reloaded.checkpoint.training_post_done is True


def test_resume_endpoint_relaunches_failed_retryable_run(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    monkeypatch.setenv("AEGIS_SHOWCASE_AUTORUN", "false")
    from app.aegis_v1 import showcase_api

    manager = ShowcaseSessionManager()
    session = manager.start_quick()
    sid = session.session_id
    manager.fail_stage(
        sid,
        stage="train_gepa",
        code="no_learning_signal",
        message="no signal",
        retryable=True,
    )

    resumed = showcase_api.resume_run(sid)

    assert resumed.status == "running"
    assert resumed.diagnostics.last_error is None
