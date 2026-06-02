"""Promotion gates adapted for multi-agent swarm candidates."""

from __future__ import annotations

from app.learning.gates import DIFF_TOKEN_CAP, evaluate_vetoes
from app.learning.models import Candidate, ExperimentResult


def _token_delta(seed: Candidate, candidate: Candidate) -> int:
    """Count only new tokens appended to changed components (not full prompt bodies)."""
    delta = 0
    for role, comp in candidate.components.items():
        prev = seed.components.get(role)
        if prev is None or prev.version == comp.version:
            continue
        prev_text = prev.text or ""
        new_text = comp.text or ""
        if new_text.startswith(prev_text):
            delta += len(new_text[len(prev_text) :].split())
        else:
            delta += abs(len(new_text.split()) - len(prev_text.split()))
    return delta


def evaluate_swarm_vetoes(
    before: ExperimentResult,
    after: ExperimentResult,
    candidate: Candidate,
    seed: Candidate,
) -> list[str]:
    """Vetoes from Part A gates, but diff cap uses append-only token delta."""
    slim = Candidate(
        candidate_id=candidate.candidate_id,
        parent_id=candidate.parent_id,
        components={
            role: comp
            for role, comp in candidate.components.items()
            if seed.components.get(role) is None
            or seed.components[role].version != comp.version
        },
        origin=candidate.origin,
        dimension_targets=candidate.dimension_targets,
        diff_summary=candidate.diff_summary,
    )
    vetoes = evaluate_vetoes(before, after, slim)
    if "diff_too_large" in vetoes:
        vetoes = [v for v in vetoes if v != "diff_too_large"]
    if _token_delta(seed, candidate) > DIFF_TOKEN_CAP:
        vetoes.append("diff_too_large")
    return vetoes
