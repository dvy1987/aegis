"""Cohen's κ judge-vs-gold calibration for the Part-A panel (v1 §10 gate).

Pure math over (judge_anchor, gold_anchor) pairs on the 1/3/5 rubric scale — fully
offline-testable. Live use: once Gemini judges run, score them against a teacher-anchored
gold set; κ ≥ 0.6 per dimension is the gate before any Gemini-judged efficacy number is
treated as official.
"""
from __future__ import annotations

from typing import Sequence

ANCHORS = (1, 3, 5)        # the only valid rubric anchors
KAPPA_GATE = 0.6


def _index(anchor: int) -> int:
    if anchor not in ANCHORS:
        raise ValueError(f"anchor must be one of {ANCHORS}, got {anchor!r}")
    return ANCHORS.index(anchor)


def cohens_kappa(judge_anchors: Sequence[int], gold_anchors: Sequence[int]) -> float:
    """Quadratic-weighted Cohen's κ on the ordinal 1/3/5 scale.

    1.0 on identical sequences; ~0 for independent raters; negative for systematic
    disagreement. Returns 1.0 when there is no expected disagreement (a degenerate
    single-category gold+judge that nonetheless agrees)."""
    if len(judge_anchors) != len(gold_anchors):
        raise ValueError("judge and gold sequences must be the same length")
    if not judge_anchors:
        raise ValueError("cannot compute kappa over an empty sequence")

    k, n = len(ANCHORS), len(judge_anchors)
    observed = [[0.0] * k for _ in range(k)]
    for j, g in zip(judge_anchors, gold_anchors):
        observed[_index(j)][_index(g)] += 1
    row = [sum(observed[i]) for i in range(k)]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    # quadratic disagreement weights on the ordinal scale (0 on the diagonal)
    weight = [[((i - j) / (k - 1)) ** 2 for j in range(k)] for i in range(k)]

    num = sum(weight[i][j] * observed[i][j] for i in range(k) for j in range(k))
    den = sum(weight[i][j] * row[i] * col[j] / n for i in range(k) for j in range(k))
    if den == 0:
        return 1.0     # no expected disagreement -> perfect agreement by convention
    return round(1 - num / den, 4)


def calibration_report(per_dimension_pairs: dict[str, list[tuple[int, int]]],
                       *, gate: float = KAPPA_GATE) -> dict:
    """Per-dimension κ + the gate verdict. `per_dimension_pairs` maps a rubric dimension
    to a list of (judge_anchor, gold_anchor) pairs."""
    kappa_by_dimension: dict[str, float] = {}
    flags: dict[str, str] = {}
    for dimension, pairs in per_dimension_pairs.items():
        kappa = cohens_kappa([p[0] for p in pairs], [p[1] for p in pairs])
        kappa_by_dimension[dimension] = kappa
        flags[dimension] = "below_gate" if kappa < gate else "ok"
    return {
        "kappa_by_dimension": kappa_by_dimension,
        "flags": flags,
        "gate": gate,
        "gate_pass": all(k >= gate for k in kappa_by_dimension.values()),
    }
