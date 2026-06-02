from app.aegis_swarm.client import StubSwarmClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.evals.part_a.recorder import InMemoryPhoenixRecorder
from app.evals.swarm.evaluated_swarm_run import run_evaluated_swarm_case


def _case() -> dict:
    return {
        "case_id": "case_demo",
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "denial_letter_text": "We denied coverage for TMS as not medically necessary.",
        "clinical_context": "Patient failed two SSRIs; severe treatment-resistant depression.",
        "patient_profile": {
            "plan_funding_type": "fully_insured",
            "diagnosis": "treatment-resistant depression",
            "treatment_requested": "TMS",
        },
        "denial_pattern_sources": [],
        "synthetic_provenance": {"appeal_difficulty": {}},
    }


def test_run_evaluated_swarm_case_closes_the_loop_offline() -> None:
    rec = InMemoryPhoenixRecorder()
    result = run_evaluated_swarm_case(
        _case(),
        rec,
        swarm_client=StubSwarmClient(),
        judge_client=OfflineHeuristicJudgeClient(),
        run_simulator=False,
    )
    assert result.appeal_package["trace_metadata"]["case_id"] == "case_demo"
    assert result.panel_report.verdict in {"PASS", "FAIL"}
    assert result.artifacts.get("agent_trace_signals")
    stored = rec.get(result.trace_ref)
    assert "weighted_quality" in stored["annotations"]
    assert stored["annotations"]["swarm_agent_trace_count"] >= 5


def test_run_evaluated_swarm_case_annotates_simulator_offline() -> None:
    rec = InMemoryPhoenixRecorder()
    result = run_evaluated_swarm_case(
        _case(),
        rec,
        swarm_client=StubSwarmClient(),
        judge_client=OfflineHeuristicJudgeClient(),
        run_simulator=True,
        simulator_client=StubSimulatorClient(assessment=uniform_assessment(1)),
    )
    assert result.simulator_result is not None
    assert result.simulator_result["verdict"] == "DENY"
    ann = rec.get(result.trace_ref)["annotations"]
    assert ann["simulator_verdict"] == "DENY"
