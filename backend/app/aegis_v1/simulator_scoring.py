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
    hard_gate: bool = False
    description: str = ""


class SimulatorRules(BaseModel):
    version: str
    anchors: list[int] = Field(default_factory=lambda: [1, 3, 5])
    approve_threshold: float
    must_have_min_anchor: int
    features: dict[str, FeatureRule]

    @model_validator(mode="after")
    def _validate_rules(self) -> "SimulatorRules":
        if self.must_have_min_anchor not in self.anchors:
            raise ValueError(
                f"must_have_min_anchor={self.must_have_min_anchor} is not in anchors={self.anchors}"
            )
        total_weight = sum(rule.weight for rule in self.features.values())
        if abs(total_weight - 1.0) > 1e-9:
            raise ValueError(f"feature weights must sum to 1.0, got {total_weight}")
        for name, rule in self.features.items():
            if rule.hard_gate and rule.weight != 0:
                raise ValueError(f"hard_gate feature {name!r} must have weight 0")
            if rule.hard_gate and rule.must_have:
                raise ValueError(f"hard_gate feature {name!r} cannot also be must_have")
        return self


def load_simulator_rules(path: str | Path | None = None) -> SimulatorRules:
    import os

    if path is not None:
        p = Path(path)
    elif os.environ.get("AEGIS_SIMULATOR_PROFILE", "").strip().lower() == "demo":
        demo_path = RULES_PATH.parent / "simulator_rules.demo.json"
        p = demo_path if demo_path.is_file() else RULES_PATH
    else:
        p = RULES_PATH
    return SimulatorRules.model_validate_json(p.read_text(encoding="utf-8"))


def score_outcome(assessment: FeatureAssessment, rules: SimulatorRules) -> SimulatorResult:
    """Deterministic verdict from LLM-assessed features + published rules (INV-S2).

  Weighted score = Σ(weight·anchor) / max_anchor across all rubric features.
  APPROVE iff score ≥ approve_threshold.

  unrebutted_denial_points are surfaced in gaps for review but do not zero the score.
    """
    feature_scores: list[FeatureScore] = []
    weighted = 0.0
    for name, rule in rules.features.items():
        mark = assessment.features.get(name) or FeatureMark(anchor=1)
        fs = FeatureScore(
            feature=name,
            anchor=mark.anchor,
            weight=rule.weight,
            must_have=rule.must_have,
            evidence=mark.evidence,
        )
        feature_scores.append(fs)
        weighted += rule.weight * mark.anchor

    max_anchor = max(rules.anchors)
    score = round(weighted / max_anchor, 4)
    hook_failures = [
        point.strip()
        for point in assessment.unrebutted_denial_points
        if point and point.strip()
    ]
    approve = score >= rules.approve_threshold
    verdict = "APPROVE" if approve else "DENY"

    gaps: list[str] = []
    if hook_failures:
        gaps.extend(f"unrebutted denial point: {point}" for point in hook_failures)
    if not approve:
        weak = [
            fs
            for fs in feature_scores
            if fs.weight > 0 and fs.anchor < max_anchor
        ]
        for fs in sorted(weak, key=lambda f: (f.anchor, -f.weight)):
            gaps.append(f"weak: {fs.feature} (anchor {fs.anchor})")

    return SimulatorResult(
        verdict=verdict, score=score, threshold=rules.approve_threshold,
        feature_scores=feature_scores, gaps=gaps,
        critique=assessment.critique,
        rationale=[assessment.critique] if assessment.critique else [],
    )
