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
