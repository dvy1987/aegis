from __future__ import annotations

from app.learning.models import Candidate

Scores = dict[str, dict[str, float]]   # candidate_id -> {case_id -> composite}


def pareto_frontier(pool: list[Candidate], scores: Scores) -> list[Candidate]:
    """Instance-wise Pareto frontier: drop candidates strictly dominated on every case
    by another (GEPA Alg. 2). A candidate survives if it is best-or-tied on >=1 case."""
    case_ids = sorted({cid for s in scores.values() for cid in s})
    survivors: list[Candidate] = []
    for cand in pool:
        s = scores.get(cand.candidate_id, {})
        dominated = False
        for other in pool:
            if other.candidate_id == cand.candidate_id:
                continue
            o = scores.get(other.candidate_id, {})
            ge_all = all(o.get(c, 0.0) >= s.get(c, 0.0) for c in case_ids)
            gt_any = any(o.get(c, 0.0) > s.get(c, 0.0) for c in case_ids)
            if ge_all and gt_any:
                dominated = True
                break
        if not dominated:
            survivors.append(cand)
    return survivors


def pareto_select(pool: list[Candidate], scores: Scores) -> Candidate:
    """Pick the parent to mutate from the Pareto frontier. Offline: deterministic argmax
    by case-win coverage (ties -> higher mean -> candidate_id). The live coordinator may
    sample stochastically with probability proportional to coverage (GEPA)."""
    front = pareto_frontier(pool, scores) or pool
    case_ids = sorted({cid for s in scores.values() for cid in s})

    def coverage(c: Candidate) -> int:
        s = scores.get(c.candidate_id, {})
        return sum(1 for cid in case_ids
                   if s.get(cid, 0.0) >= max(scores.get(o.candidate_id, {}).get(cid, 0.0) for o in front))

    def mean(c: Candidate) -> float:
        s = scores.get(c.candidate_id, {})
        return sum(s.values()) / len(s) if s else 0.0

    return max(front, key=lambda c: (coverage(c), mean(c), c.candidate_id))


def select_component(parent: Candidate, round_index: int) -> str:
    """Round-robin across the candidate's components so every lever (global prompt and
    each per-slice playbook) receives updates over the run (GEPA module round-robin,
    v2 spec §4.2). Deterministic: sorted ids indexed by the round."""
    ids = sorted(parent.components)
    return ids[round_index % len(ids)]
