import pytest
from pydantic import ValidationError

from app.aegis_v1.schemas import (
    FeatureAssessment,
    FeatureMark,
    FeatureScore,
    SimulatorResult,
)


def test_feature_mark_rejects_non_anchor_value():
    with pytest.raises(ValidationError):
        FeatureMark(anchor=2)  # only 1/3/5 allowed


def test_feature_assessment_holds_keyed_marks():
    fa = FeatureAssessment(
        critique="c",
        features={"rebuts_specific_flaw": FeatureMark(anchor=5, evidence="q")},
    )
    assert fa.features["rebuts_specific_flaw"].anchor == 5


def test_simulator_result_accepts_float_score_and_breakdown():
    r = SimulatorResult(
        verdict="DENY", score=0.38, threshold=0.70,
        feature_scores=[FeatureScore(
            feature="rebuts_specific_flaw", anchor=1, weight=0.15, must_have=False)],
        gaps=["weak: rebuts_specific_flaw (anchor 1)"], critique="weak",
    )
    assert r.score == 0.38
    assert r.verdict == "DENY"


from app.aegis_v1.simulator_scoring import load_simulator_rules, SimulatorRules

FEATURE_KEYS = {
    "addresses_denial_rationale",
    "cites_clinical_evidence",
    "cites_applicable_authority",
    "cites_binding_policy",
    "rebuts_specific_flaw",
    "medical_director_persuasion",
    "specific_requested_action",
    "credible_tone",
}


def test_load_simulator_rules_parses_published_file():
    rules = load_simulator_rules()
    assert rules.version
    assert set(rules.features) == FEATURE_KEYS
    assert abs(sum(f.weight for f in rules.features.values()) - 1.0) < 1e-9
    assert rules.approve_threshold == 0.80
    for name, rule in rules.features.items():
        assert rule.hard_gate is False
        assert rule.must_have is False
        assert rule.weight > 0, name


def test_feature_rule_rejects_out_of_range_weight():
    bad = '{"version":"x","approve_threshold":0.7,"must_have_min_anchor":3,' \
          '"features":{"f":{"weight":2.5,"must_have":false,"description":"d"}}}'
    with pytest.raises(ValidationError):
        SimulatorRules.model_validate_json(bad)


def test_rules_reject_must_have_min_anchor_not_in_anchors():
    bad = '{"version":"x","anchors":[1,3,5],"approve_threshold":0.7,' \
          '"must_have_min_anchor":4,"features":{}}'
    with pytest.raises(ValidationError):
        SimulatorRules.model_validate_json(bad)


def test_rules_reject_hard_gate_with_nonzero_weight():
    bad = (
        '{"version":"x","anchors":[1,3,5],"approve_threshold":0.8,"must_have_min_anchor":5,'
        '"features":{"g":{"weight":0.1,"hard_gate":true,"must_have":false,"description":"d"},'
        '"f":{"weight":0.9,"hard_gate":false,"must_have":false,"description":"d"}}}'
    )
    with pytest.raises(ValidationError):
        SimulatorRules.model_validate_json(bad)


from app.aegis_v1.simulator_scoring import score_outcome

ALL_KEYS = [
    "addresses_denial_rationale",
    "cites_clinical_evidence",
    "cites_applicable_authority",
    "cites_binding_policy",
    "rebuts_specific_flaw",
    "medical_director_persuasion",
    "specific_requested_action",
    "credible_tone",
]


def _assess(anchors: dict[str, int], critique: str = "c") -> FeatureAssessment:
    return FeatureAssessment(
        critique=critique,
        features={k: FeatureMark(anchor=v) for k, v in anchors.items()},
    )


def test_unrebutted_denial_points_are_advisory_and_do_not_zero_score():
    rules = load_simulator_rules()
    res = score_outcome(
        FeatureAssessment(
            critique="Age and duration hooks not rebutted.",
            features={k: FeatureMark(anchor=5) for k in ALL_KEYS},
            unrebutted_denial_points=[
                "age 22-68 eligibility criteria not rebutted",
                "36-session duration cap not rebutted as standard acute course",
            ],
        ),
        rules,
    )
    assert res.verdict == "APPROVE"
    assert res.score == 1.0
    assert any("unrebutted denial point" in g for g in res.gaps)


def test_all_fives_approve_with_no_gaps():
    rules = load_simulator_rules()
    res = score_outcome(_assess({k: 5 for k in ALL_KEYS}), rules)
    assert res.verdict == "APPROVE"
    assert res.score == 1.0
    assert res.gaps == []


def test_weak_v1_denies_below_threshold():
    rules = load_simulator_rules()
    res = score_outcome(_assess({
        "addresses_denial_rationale": 3,
        "cites_clinical_evidence": 1,
        "cites_applicable_authority": 1,
        "cites_binding_policy": 1,
        "rebuts_specific_flaw": 1,
        "medical_director_persuasion": 1,
        "specific_requested_action": 3,
        "credible_tone": 3,
    }), rules)
    assert res.verdict == "DENY"
    assert res.score == pytest.approx(0.35, abs=0.01)
    assert any("weak: rebuts_specific_flaw" in g for g in res.gaps)


def test_low_authority_anchor_still_allows_approve_when_weighted_score_high():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["cites_applicable_authority"] = 1
    res = score_outcome(_assess(anchors), rules)
    assert res.verdict == "APPROVE"
    assert res.score == pytest.approx(0.93, abs=0.01)


def test_partial_rebut_anchors_can_still_approve():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["rebuts_specific_flaw"] = 3
    anchors["addresses_denial_rationale"] = 3
    res = score_outcome(_assess(anchors), rules)
    assert res.verdict == "APPROVE"
    assert res.score == pytest.approx(0.82, abs=0.01)


def test_partial_medical_director_anchor_does_not_zero_score():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["medical_director_persuasion"] = 3
    res = score_outcome(_assess(anchors), rules)
    assert res.verdict == "APPROVE"
    assert res.score == pytest.approx(0.94, abs=0.02)


def test_missing_feature_is_treated_as_anchor_1():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS if k != "cites_clinical_evidence"}
    res = score_outcome(_assess(anchors), rules)
    cs = {fs.feature: fs.anchor for fs in res.feature_scores}
    assert cs["cites_clinical_evidence"] == 1
    assert res.verdict == "APPROVE"
    assert res.score == pytest.approx(0.92, abs=0.01)
