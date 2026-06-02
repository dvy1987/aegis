from app.aegis_swarm.client import StubSwarmClient
from app.evals.part_a.llm_judges import OfflineHeuristicJudgeClient
from app.learning.swarm_counterfactual import run_swarm_counterfactual


def _case(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "insurer": "Cigna",
        "denial_type": "Medical Necessity",
        "denial_letter_text": "We denied TMS as not medically necessary.",
        "clinical_context": "Failed two SSRIs.",
        "patient_profile": {"plan_funding_type": "fully_insured"},
        "denial_pattern_sources": [],
        "synthetic_provenance": {"appeal_difficulty": {}},
    }


def test_swarm_counterfactual_mcp_on_beats_off() -> None:
    res = run_swarm_counterfactual(
        [_case("c1"), _case("c2")],
        swarm_client=StubSwarmClient(),
        judge_client=OfflineHeuristicJudgeClient(),
    )
    assert res["on_composite"] > res["off_composite"]
    assert res["delta"] > 0
    assert len(res["per_case"]) == 2
    for row in res["per_case"]:
        assert row["delta"] > 0
        assert row["phoenix_memory_active_on"] is True
        assert row["phoenix_memory_degraded_off"] is True
