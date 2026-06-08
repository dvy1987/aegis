from __future__ import annotations

from app.learning.models import Candidate, ExperimentResult

DIFF_TOKEN_CAP = 200


def _diff_tokens(candidate: Candidate) -> int:
    """Rough token proxy: whitespace tokens across all component bodies."""
    total = 0
    for comp in candidate.components.values():
        if comp.text:
            total += len(comp.text.split())
        if comp.playbook:
            total += len(str(comp.playbook).split())
    return total


def evaluate_vetoes(before: ExperimentResult, after: ExperimentResult,
                    candidate: Candidate, *, diff_token_cap: int = DIFF_TOKEN_CAP) -> list[str]:
    """Non-LLM promotion gates (v1 §8.2). A candidate is promotable only if this is empty
    AND composite improved. Mostly deterministic so judge bias can't drive promotions."""
    vetoes: list[str] = []
    if after.composite < before.composite:
        vetoes.append("held_out_regression")
    if any(not c.hard_gate_pass for c in after.per_case):
        vetoes.append("safety_or_hard_gate_regression")
    if _diff_tokens(candidate) > diff_token_cap:
        vetoes.append("diff_too_large")
    return vetoes
