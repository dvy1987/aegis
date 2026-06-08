from app.evals.part_a.evaluated_run import run_evaluated_case
from app.evals.part_a.recorder import InMemoryPhoenixRecorder
from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient


def _case():
    return {
        "case_id": "case_demo", "insurer": "Cigna", "denial_type": "Medical Necessity",
        "denial_letter_text": "We denied coverage for TMS as not medically necessary.",
        "clinical_context": "Patient failed two SSRIs; severe treatment-resistant depression.",
        "patient_profile": {"plan_funding_type": "fully_insured",
                            "diagnosis": "treatment-resistant depression",
                            "treatment_requested": "TMS"},
        "denial_pattern_sources": [], "synthetic_provenance": {"appeal_difficulty": {}},
    }


def test_run_evaluated_case_closes_the_loop_offline():
    rec = InMemoryPhoenixRecorder()
    result = run_evaluated_case(
        _case(),
        recorder=rec,
        drafter_client=StubDrafterClient(),
        judge_client=OfflineHeuristicJudgeClient(),
        run_simulator=False,   # no GCP in dev
    )
    assert result.appeal_package["trace_metadata"]["case_id"] == "case_demo"
    assert result.panel_report.verdict in {"PASS", "FAIL"}
    stored = rec.get(result.trace_ref)
    # laundered signal landed on the trace
    assert "weighted_quality" in stored["annotations"]
    assert "dimensions" in stored["annotations"]


def test_run_evaluated_case_does_not_annotate_simulator_on_phoenix() -> None:
    """D12: simulator scores never written to Phoenix annotations."""
    rec = InMemoryPhoenixRecorder()
    result = run_evaluated_case(
        _case(),
        recorder=rec,
        drafter_client=StubDrafterClient(),
        judge_client=OfflineHeuristicJudgeClient(),
        run_simulator=True,
        simulator_client=StubSimulatorClient(assessment=uniform_assessment(1)),
    )
    assert result.simulator_result["verdict"] == "DENY"
    ann = rec.get(result.trace_ref)["annotations"]
    assert "simulator_verdict" not in ann
    assert "simulator_score" not in ann
