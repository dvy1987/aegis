"""Phase 3 showcase evaluate reliability tests."""

from __future__ import annotations

from app.aegis_v1 import showcase_api
from app.evals.part_a.evaluated_run import EvaluatedRun
from app.evals.part_a.schemas import PanelReport


def _panel_report() -> PanelReport:
    from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
    from app.evals.part_a.panel import run_panel
    from app.evals.part_a.teacher_packet import build_teacher_grading_packet

    case = showcase_api._benchmark_case_obj(
        case_id="eval_test",
        denial_letter_text="Cigna denied IOP.",
        clinical_context="Severe OCD.",
    )
    appeal = {
        "appeal_package_draft": {
            "appeal_letter": "Not legal or medical advice. Draft assistance only. Appeal.",
            "citations_used": [],
            "missing_evidence_checklist": [],
        }
    }
    teacher = build_teacher_grading_packet(case, appeal)
    return run_panel(appeal, teacher, OfflineHeuristicJudgeClient())


def _evaluated_run() -> EvaluatedRun:
    report = _panel_report()
    return EvaluatedRun(
        appeal_package={
            "appeal_package_draft": {"appeal_letter": "x"},
            "trace_metadata": {},
        },
        panel_report=report,
        simulator_result={"verdict": "DENY", "score": 0.2},
        trace_ref="abc123",
    )


def test_evaluate_same_prompt_version_runs_pipeline_once(monkeypatch) -> None:
    calls: list[str | None] = []

    def fake_run_evaluated_case(_case, **kwargs):
        calls.append(kwargs.get("drafter_prompt_version"))
        return _evaluated_run()

    monkeypatch.setattr(showcase_api, "run_evaluated_case", fake_run_evaluated_case)
    monkeypatch.setattr(
        "app.aegis_v1.simulator_client.AdkSimulatorClient",
        lambda **_: object(),
    )

    req = showcase_api.ShowcaseEvaluateRequest(
        case_id="same_prompt",
        denial_letter_text="Denied.",
        clinical_context="OCD.",
        baseline_prompt_version="drafter_v1",
        candidate_prompt_version="drafter_v1",
        judge_mode="fast",
        run_counterfactual=False,
    )
    bundle = showcase_api.evaluate_showcase(req)

    assert len(calls) == 1
    assert bundle.lift_relative_pct == 0.0
