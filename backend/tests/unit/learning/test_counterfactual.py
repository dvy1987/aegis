from app.learning.counterfactual import run_counterfactual

DIMS = ["grounding", "appeal_vector_capture", "case_specific_clinical_rebuttal",
        "evidence_completeness", "persuasive_coherence"]


def _lookup_on(case):
    return {"disabled": False, "failure_patterns": ["missed_peer_to_peer"]}


def _lookup_off(case):
    return {"disabled": True, "failure_patterns": []}


def _drafter(case, phoenix_summary):
    # a drafter that actually uses Phoenix memory writes a stronger letter when it is available
    if not phoenix_summary.get("disabled") and phoenix_summary.get("failure_patterns"):
        return "strong: " + ", ".join(phoenix_summary["failure_patterns"])
    return "weak generic letter"


class _FakeJudge:
    def score(self, *, case, appeal_letter, simulator_verdict=None):
        strong = appeal_letter.startswith("strong:")
        return {"dimension_scores": {d: (5 if strong else 3) for d in DIMS},
                "hard_gate_pass": True}


def test_counterfactual_mcp_on_beats_off():
    res = run_counterfactual(
        [{"case_id": "c1"}, {"case_id": "c2"}],
        drafter=_drafter, judge_adapter=_FakeJudge(),
        lookup_on=_lookup_on, lookup_off=_lookup_off)
    assert res["on_composite"] > res["off_composite"]
    assert res["delta"] > 0
    assert len(res["per_case"]) == 2
    assert res["per_case"][0]["delta"] > 0
