from __future__ import annotations

from app.evals.part_a.schemas import PanelReport
from app.learning.experiment import LiveExperimentRunner
from app.learning.models import Candidate, Component


class _RecordingRecorder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record_run(self, appeal_package, trace_metadata) -> str:
        self.calls.append({"package": appeal_package, "metadata": dict(trace_metadata)})
        return f"trace-{len(self.calls)}"

    def annotate(self, trace_ref, annotations) -> None:
        self.calls.append({"trace_ref": trace_ref, "annotations": annotations})


class _FakeJudge:
    def score(self, *, case, appeal_letter):
        return {
            "dimension_scores": {"grounding": 3, "appeal_vector_capture": 3},
            "hard_gate_pass": True,
            "weighted_quality": 0.5,
        }


def test_live_runner_persists_tier_b_metadata(monkeypatch) -> None:
    recorder = _RecordingRecorder()
    panel_report = PanelReport(
        case_id="t1",
        verdict="PASS",
        dimension_scores={"grounding": 3, "appeal_vector_capture": 3},
        weighted_quality=0.5,
        judge_results={},
        weights={},
    )

    seen: list[dict] = []

    def fake_run_evaluated_case(case_obj, **kwargs):
        seen.append(kwargs)
        assert kwargs["recorder"] is recorder
        assert kwargs["trace_tags"]["memory_eligible"] == "false"
        assert kwargs["trace_tags"]["candidate_id"] == "c1"
        assert kwargs["run_mode"] == "gepa_optimize_candidate"
        return type("Run", (), {"panel_report": panel_report})()

    monkeypatch.setattr(
        "app.learning.experiment._run_evaluated_case",
        fake_run_evaluated_case,
    )

    dataset = [
        {
            "case_id": "t1",
            "slice": "Cigna:medical_necessity",
            "denial_letter_text": "denial",
            "clinical_context": "ctx",
            "parsed_case": {"case_id": "t1"},
        }
    ]
    candidate = Candidate(
        candidate_id="c1",
        components={
            "drafter_system_prompt": Component(
                component_id="drafter_system_prompt",
                kind="prompt",
                version="v2",
                text="prompt",
            ),
            "playbook:Cigna:medical_necessity": Component(
                component_id="playbook:Cigna:medical_necessity",
                kind="playbook",
                version="v2",
                playbook={"tactics": []},
            ),
        },
        origin="reflect",
    )
    runner = LiveExperimentRunner(
        dataset,
        judge_client=_FakeJudge(),
        recorder=recorder,
        memory_eligible=False,
    )
    result = runner.run(candidate, dataset_split="showcase_train", gepa_round=1)
    assert result.composite > 0
    assert len(seen) == 1
    assert seen[0]["trace_tags"]["gepa_round"] == 1
