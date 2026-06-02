from app.learning.autonomy_ladder import AutonomyLadder, AutonomyStage
from app.learning.models import (
    Candidate, CaseScore, Component, ExperimentResult, PromotionProposal,
)


def _proposal(mutated_role: str, promotable: bool = True) -> PromotionProposal:
    comp = Component(component_id=mutated_role, kind="prompt", version="v2", text="x")
    cand = Candidate(
        candidate_id="c1",
        components={mutated_role: comp},
        origin="reflect",
        diff_summary=f"reflect {mutated_role} for grounding: v1->v2",
    )
    before = ExperimentResult(candidate_id="seed", dataset_split="holdout", composite=0.5)
    after = ExperimentResult(
        candidate_id="c1",
        dataset_split="holdout",
        composite=0.7 if promotable else 0.4,
        per_case=[CaseScore(case_id="a", composite=0.7, dimension_scores={}, hard_gate_pass=True)],
    )
    return PromotionProposal(
        candidate=cand, before=before, after=after, per_dimension_deltas={}, vetoes=[] if promotable else ["held_out_regression"],
    )


def test_apprentice_requires_hitl():
    ladder = AutonomyLadder()
    assert ladder.requires_hitl(_proposal("strategist"))


def test_master_blocks_autonomous_adversarial_promotion():
    ladder = AutonomyLadder()
    ladder.state.stage = AutonomyStage.MASTER
    assert not ladder.may_auto_promote(_proposal("adversarial_reviewer"))


def test_journeyman_allows_strategist_auto_when_promotable():
    ladder = AutonomyLadder()
    ladder.state.stage = AutonomyStage.JOURNEYMAN
    assert ladder.may_auto_promote(_proposal("strategist"))


def test_circuit_breaker_demotes_master():
    ladder = AutonomyLadder()
    ladder.state.stage = AutonomyStage.MASTER
    for score in [0.80, 0.79, 0.78, 0.77, 0.76, 0.75, 0.74, 0.73, 0.72, 0.60]:
        ladder.record_holdout(score)
    assert ladder.state.stage == AutonomyStage.JOURNEYMAN
