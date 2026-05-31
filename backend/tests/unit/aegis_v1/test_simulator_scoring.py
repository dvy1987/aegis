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
        gaps=["must-have not met: rebuts_specific_flaw"], critique="weak",
    )
    assert r.score == 0.38
    assert r.verdict == "DENY"
    assert r.feature_scores[0].must_have is True


from app.aegis_v1.simulator_scoring import load_simulator_rules, SimulatorRules

FEATURE_KEYS = {
    "addresses_denial_rationale", "cites_clinical_evidence", "cites_binding_policy",
    "rebuts_specific_flaw", "specific_requested_action", "credible_tone",
}


def test_load_simulator_rules_parses_published_file():
    rules = load_simulator_rules()
    assert rules.version
    assert set(rules.features) == FEATURE_KEYS
    assert abs(sum(f.weight for f in rules.features.values()) - 1.0) < 1e-9
    assert rules.approve_threshold == 0.70
    assert rules.must_have_min_anchor == 3
    assert rules.features["rebuts_specific_flaw"].must_have is True


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
