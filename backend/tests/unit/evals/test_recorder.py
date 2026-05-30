from app.evals.part_a.recorder import (
    InMemoryPhoenixRecorder,
    OtelPhoenixRecorder,
    laundered_signal,
)
from app.evals.part_a.schemas import JudgeResult, PanelReport


def _panel_with_leaky_quote():
    return PanelReport(
        case_id="c1", verdict="PASS", weighted_quality=0.6,
        hard_gate_failures=[], promotion_blockers=[],
        dimension_scores={"appeal_vector_capture": 3},
        judge_results={"appeal_vector_capture": JudgeResult(
            dimension="appeal_vector_capture", reasoning="missed the embedded flaw",
            score=3, confidence=0.6,
            evidence_quotes=["SECRET expected vector", "full and fair review"],
            improvement="Attack the specific denial defect.")},
        weights={"appeal_vector_capture": 0.25}, risk_flags=[], metadata={})


def test_laundered_signal_drops_quotes_not_in_letter():
    letter = "We request a full and fair review of the denial."
    out = laundered_signal(_panel_with_leaky_quote(), appeal_letter=letter)
    dim = out["dimensions"]["appeal_vector_capture"]
    assert dim["improvement"] == "Attack the specific denial defect."
    assert "full and fair review" in dim["evidence_quotes"]
    assert "SECRET expected vector" not in dim["evidence_quotes"]   # firewall


def test_in_memory_recorder_round_trips_run_and_annotation():
    rec = InMemoryPhoenixRecorder()
    ref = rec.record_run({"run_id": "r1"}, {"case_id": "c1", "insurer": "Cigna"})
    rec.annotate(ref, {"weighted_quality": 0.6})
    stored = rec.get(ref)
    assert stored["metadata"]["insurer"] == "Cigna"
    assert stored["annotations"]["weighted_quality"] == 0.6


def test_otel_recorder_has_expected_name_and_project(monkeypatch):
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "default")
    rec = OtelPhoenixRecorder()
    assert rec.name == "otel_phoenix"
    assert rec.project_name == "default"
