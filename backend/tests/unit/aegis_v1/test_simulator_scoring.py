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
            feature="rebuts_specific_flaw", anchor=1, weight=0.20, must_have=True)],
        gaps=["hard gate not met: rebuts_specific_flaw"], critique="weak",
    )
    assert r.score == 0.38
    assert r.verdict == "DENY"
    assert r.feature_scores[0].must_have is True


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

HARD_GATES = {
    "addresses_denial_rationale",
    "cites_applicable_authority",
    "rebuts_specific_flaw",
    "medical_director_persuasion",
}


def test_load_simulator_rules_parses_published_file():
    rules = load_simulator_rules()
    assert rules.version
    assert set(rules.features) == FEATURE_KEYS
    assert abs(sum(f.weight for f in rules.features.values()) - 1.0) < 1e-9
    assert rules.approve_threshold == 0.80
    assert rules.must_have_min_anchor == 5
    assert rules.features["cites_clinical_evidence"].must_have is True
    for name in HARD_GATES:
        assert rules.features[name].hard_gate is True
        assert rules.features[name].weight == 0.0


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

WEIGHTED_KEYS = [k for k in ALL_KEYS if k not in HARD_GATES]


def _assess(anchors: dict[str, int], critique: str = "c") -> FeatureAssessment:
    return FeatureAssessment(
        critique=critique,
        features={k: FeatureMark(anchor=v) for k, v in anchors.items()},
    )


def test_unrebutted_denial_points_hard_deny_even_with_perfect_features():
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
    assert res.verdict == "DENY"
    assert res.score == 0.0
    assert any("unrebutted denial point" in g for g in res.gaps)


def test_all_fives_approve_with_no_gaps():
    rules = load_simulator_rules()
    res = score_outcome(_assess({k: 5 for k in ALL_KEYS}), rules)
    assert res.verdict == "APPROVE"
    assert res.score == 1.0
    assert res.gaps == []


def test_weak_v1_denies_below_threshold_and_hard_gate_failures():
    rules = load_simulator_rules()
    res = score_outcome(_assess({
        "addresses_denial_rationale": 3,
        "cites_clinical_evidence": 1,
        "cites_applicable_authority": 1,
        "cites_binding_policy": 1,
        "rebuts_specific_flaw": 1,
        "specific_requested_action": 3,
        "credible_tone": 3,
    }), rules)
    assert res.verdict == "DENY"
    assert res.score == 0.0
    assert any("hard gate not met" in g and "rebuts_specific_flaw" in g for g in res.gaps)
    assert any("hard gate not met" in g and "cites_applicable_authority" in g for g in res.gaps)


def test_cites_applicable_authority_hard_gate_deny_with_perfect_weighted_score():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["cites_applicable_authority"] = 1
    res = score_outcome(_assess(anchors), rules)
    assert res.verdict == "DENY"
    assert res.score == 0.0
    assert any("hard gate not met: cites_applicable_authority" in g for g in res.gaps)


def test_hard_gate_rebut_deny_with_perfect_weighted_score():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["rebuts_specific_flaw"] = 1
    res = score_outcome(_assess(anchors), rules)
    assert res.score == 0.0
    assert res.verdict == "DENY"
    assert any("hard gate not met: rebuts_specific_flaw" in g for g in res.gaps)


def test_partial_hard_gate_anchor_3_denies():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["rebuts_specific_flaw"] = 3
    anchors["addresses_denial_rationale"] = 3
    res = score_outcome(_assess(anchors), rules)
    assert res.verdict == "DENY"
    assert any("hard gate not met: rebuts_specific_flaw" in g for g in res.gaps)
    assert any("hard gate not met: addresses_denial_rationale" in g for g in res.gaps)


def test_medical_director_persuasion_hard_gate_zeros_score():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["medical_director_persuasion"] = 3
    res = score_outcome(_assess(anchors), rules)
    assert res.verdict == "DENY"
    assert res.score == 0.0
    assert any("hard gate not met: medical_director_persuasion" in g for g in res.gaps)


def test_partial_must_have_anchor_3_denies():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS}
    anchors["cites_clinical_evidence"] = 3
    res = score_outcome(_assess(anchors), rules)
    assert res.verdict == "DENY"
    assert any("must-have not met: cites_clinical_evidence" in g for g in res.gaps)


def test_missing_feature_is_treated_as_anchor_1():
    rules = load_simulator_rules()
    anchors = {k: 5 for k in ALL_KEYS if k != "cites_clinical_evidence"}
    res = score_outcome(_assess(anchors), rules)
    cs = {fs.feature: fs.anchor for fs in res.feature_scores}
    assert cs["cites_clinical_evidence"] == 1
    assert res.verdict == "DENY"
    assert any("must-have not met: cites_clinical_evidence" in g for g in res.gaps)
