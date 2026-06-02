"""Three-stage autonomy ladder for swarm prompt promotion (FR-3)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.learning.credit_resolution import MASTER_AUTONOMY_FORBIDDEN
from app.learning.models import Candidate, PromotionProposal


class AutonomyStage(str, Enum):
    APPRENTICE = "apprentice"
    JOURNEYMAN = "journeyman"
    MASTER = "master"


class AutonomyState(BaseModel):
    stage: AutonomyStage = AutonomyStage.APPRENTICE
    pm_approved_count: int = 0
    auto_promotion_count: int = 0
    recent_holdout_composites: list[float] = Field(default_factory=list)


class AutonomyLadder:
    """Stage gates per ``docs/specs/2026-05-27-autonomy-ladder-design.md``."""

    JOURNEYMAN_APPROVALS = 10
    JOURNEYMAN_COMPOSITE = 0.60
    MASTER_AUTO_PROMOTIONS = 25
    MASTER_COMPOSITE = 0.75
    CIRCUIT_BREAKER_DROP = 0.10
    CIRCUIT_WINDOW = 10

    def __init__(self, state: AutonomyState | None = None) -> None:
        self.state = state or AutonomyState()

    def record_holdout(self, composite: float) -> None:
        self.state.recent_holdout_composites.append(composite)
        if len(self.state.recent_holdout_composites) > self.CIRCUIT_WINDOW:
            self.state.recent_holdout_composites = self.state.recent_holdout_composites[
                -self.CIRCUIT_WINDOW :
            ]
        self._check_circuit_breaker()

    def _check_circuit_breaker(self) -> None:
        scores = self.state.recent_holdout_composites
        if len(scores) < self.CIRCUIT_WINDOW:
            return
        peak = max(scores)
        latest = scores[-1]
        if peak > 0 and (peak - latest) / peak > self.CIRCUIT_BREAKER_DROP:
            if self.state.stage == AutonomyStage.MASTER:
                self.state.stage = AutonomyStage.JOURNEYMAN

    def note_pm_approval(self) -> None:
        self.state.pm_approved_count += 1
        self._maybe_promote_stage()

    def note_auto_promotion(self) -> None:
        self.state.auto_promotion_count += 1
        self._maybe_promote_stage()

    def _maybe_promote_stage(self) -> None:
        if (
            self.state.stage == AutonomyStage.APPRENTICE
            and self.state.pm_approved_count >= self.JOURNEYMAN_APPROVALS
            and self._rolling_composite() >= self.JOURNEYMAN_COMPOSITE
        ):
            self.state.stage = AutonomyStage.JOURNEYMAN
        if (
            self.state.stage == AutonomyStage.JOURNEYMAN
            and self.state.auto_promotion_count >= self.MASTER_AUTO_PROMOTIONS
            and self._rolling_composite() >= self.MASTER_COMPOSITE
        ):
            self.state.stage = AutonomyStage.MASTER

    def _rolling_composite(self) -> float:
        scores = self.state.recent_holdout_composites
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def may_auto_promote(self, proposal: PromotionProposal) -> bool:
        if not proposal.is_promotable:
            return False
        mutated = _mutated_roles(proposal.candidate)
        if self.state.stage == AutonomyStage.APPRENTICE:
            return False
        if self.state.stage == AutonomyStage.MASTER:
            if mutated & MASTER_AUTONOMY_FORBIDDEN:
                return False
            return True
        # Journeyman: auto allowed except safety reviewer (still HITL for adversarial)
        if mutated & MASTER_AUTONOMY_FORBIDDEN:
            return False
        return True

    def requires_hitl(self, proposal: PromotionProposal) -> bool:
        return not self.may_auto_promote(proposal)


def _mutated_roles(candidate: Candidate) -> set[str]:
    if candidate.origin == "seed" or "reflect " not in candidate.diff_summary:
        return set()
    role = candidate.diff_summary.split("reflect ", 1)[1].split(" for", 1)[0].strip()
    return {role} if role else set()
