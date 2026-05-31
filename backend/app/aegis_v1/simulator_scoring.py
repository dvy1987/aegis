from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

# backend/app/aegis_v1/simulator_scoring.py -> parents[3] is the repo root; eval/ lives there.
RULES_PATH = Path(__file__).resolve().parents[3] / "eval" / "simulator_rules.json"


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
