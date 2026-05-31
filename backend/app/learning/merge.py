from __future__ import annotations

from app.learning.models import Candidate, Component


def _changed(cand: Candidate, base: Candidate) -> set[str]:
    return {cid for cid, comp in cand.components.items()
            if base.components.get(cid) is None or base.components[cid].version != comp.version}


def system_aware_merge(a: Candidate, b: Candidate, *, base: Candidate,
                       next_id: str) -> Candidate | None:
    """Combine two lineages that improved DIFFERENT components (GEPA Appendix F).
    Returns None if they edited the same component (conflict → escalate/skip)."""
    changed_a, changed_b = _changed(a, base), _changed(b, base)
    if changed_a & changed_b:
        return None
    components: dict[str, Component] = dict(base.components)
    for cid in changed_a:
        components[cid] = a.components[cid]
    for cid in changed_b:
        components[cid] = b.components[cid]
    return Candidate(
        candidate_id=next_id, parent_id=a.candidate_id, components=components, origin="merge",
        dimension_targets=sorted(set(a.dimension_targets) | set(b.dimension_targets)),
        diff_summary=f"merge {a.candidate_id}+{b.candidate_id}: {sorted(changed_a)}|{sorted(changed_b)}",
    )
