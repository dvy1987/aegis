from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from app.aegis_v1.schemas import (
    FeatureAssessment,
    FeatureMark,
    FeatureScore,
    SimulatorResult,
)

# backend/app/aegis_v1/simulator_scoring.py -> parents[3] is the repo root; eval/ lives there.
RULES_PATH = Path(__file__).resolve().parents[2] / "simulator_rules.json"


class FeatureRule(BaseModel):
    weight: Annotated[float, Field(ge=0.0, le=1.0)]
    must_have: bool = False
    description: str = ""


class SimulatorRules(BaseModel):
    version: str
    anchors: list[int] = Field(default_factory=lambda: [1, 3, 5])
    approve_threshold: float
    must_have_min_anchor: int
    features: dict[str, FeatureRule]

    @model_validator(mode="after")
    def _must_have_anchor_in_anchors(self) -> "SimulatorRules":
        if self.must_have_min_anchor not in self.anchors:
            raise ValueError(
                f"must_have_min_anchor={self.must_have_min_anchor} is not in anchors={self.anchors}"
            )
        return self


def load_simulator_rules(path: str | Path | None = None) -> SimulatorRules:
    p = Path(path) if path else RULES_PATH
    return SimulatorRules.model_validate_json(p.read_text(encoding="utf-8"))


def score_outcome(assessment: FeatureAssessment, rules: SimulatorRules) -> SimulatorResult:
    """Deterministic verdict from LLM-assessed features + published rules (INV-S2).

    score = Σ(weight·anchor) / max_anchor, in [0.2, 1.0]. APPROVE iff
    score ≥ approve_threshold AND every must-have feature ≥ must_have_min_anchor.
    """
    feature_scores: list[FeatureScore] = []
    must_have_failures: list[FeatureScore] = []
    weighted = 0.0
    for name, rule in rules.features.items():
        mark = assessment.features.get(name) or FeatureMark(anchor=1)
        fs = FeatureScore(
            feature=name, anchor=mark.anchor, weight=rule.weight,
            must_have=rule.must_have, evidence=mark.evidence,
        )
        feature_scores.append(fs)
        weighted += rule.weight * mark.anchor
        if rule.must_have and mark.anchor < rules.must_have_min_anchor:
            must_have_failures.append(fs)

    max_anchor = max(rules.anchors)
    score = round(weighted / max_anchor, 4)
    approve = (not must_have_failures) and score >= rules.approve_threshold
    verdict = "APPROVE" if approve else "DENY"

    gaps: list[str] = []
    if not approve:
        for fs in must_have_failures:
            gaps.append(
                f"must-have not met: {fs.feature} "
                f"(anchor {fs.anchor} < {rules.must_have_min_anchor})"
            )
        failed = {fs.feature for fs in must_have_failures}
        weak = [fs for fs in feature_scores if fs.feature not in failed and fs.anchor < max_anchor]
        for fs in sorted(weak, key=lambda f: (f.anchor, -f.weight)):
            gaps.append(f"weak: {fs.feature} (anchor {fs.anchor})")

    return SimulatorResult(
        verdict=verdict, score=score, threshold=rules.approve_threshold,
        feature_scores=feature_scores, gaps=gaps,
        critique=assessment.critique,
        rationale=[assessment.critique] if assessment.critique else [],
    )
