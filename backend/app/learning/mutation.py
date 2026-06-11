from __future__ import annotations

from app.learning.models import Candidate, DimensionSignal, ScoredRun
from app.learning.reflection_client import ReflectionClient


def reflective_mutate(parent: Candidate, signal: DimensionSignal,
                      reflection_client: ReflectionClient, *, minibatch: list[ScoredRun],
                      next_id: str) -> Candidate:
    """GEPA reflective mutation: revise EXACTLY the targeted component, copy the rest,
    record lineage + dimension credit. Small, attributable diffs (V2-INV-2)."""
    target = signal.component_id
    revised = reflection_client.reflect(
        component=parent.components[target], signal=signal, minibatch=minibatch)
    components = dict(parent.components)
    components[target] = revised
    critique_note = ""
    if revised.reflection_critique:
        critique_note = f" | critique: {revised.reflection_critique[:120]}"
    return Candidate(
        candidate_id=next_id, parent_id=parent.candidate_id, components=components,
        origin="reflect", dimension_targets=[signal.weakest_dimension],
        diff_summary=(
            f"reflect {target} for {signal.weakest_dimension}: "
            f"{parent.components[target].version}->{revised.version}{critique_note}"
        ),
    )
