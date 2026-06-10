from __future__ import annotations

from app.aegis_v1.geo_playbook import US_PLAYBOOK_COMPONENT_ID, append_us_rule, bump_geo_version
from app.learning.models import Candidate, DimensionSignal, ScoredRun
from app.learning.reflection_client import ReflectionClient


def reflective_mutate_geo(
    parent: Candidate,
    signal: DimensionSignal,
    reflection_client: ReflectionClient,
    *,
    minibatch: list[ScoredRun],
    next_id: str,
) -> Candidate:
    """GEPA reflective mutation for ``geo_playbook:us`` (append-first US rules)."""
    target = US_PLAYBOOK_COMPONENT_ID
    revised = reflection_client.reflect(
        component=parent.components[target],
        signal=signal,
        minibatch=minibatch,
    )
    components = dict(parent.components)
    components[target] = revised
    return Candidate(
        candidate_id=next_id,
        parent_id=parent.candidate_id,
        components=components,
        origin="reflect",
        dimension_targets=[signal.weakest_dimension],
        diff_summary=(
            f"reflect {target} for {signal.weakest_dimension}: "
            f"{parent.components[target].version}->{revised.version}"
        ),
    )


def stub_append_geo_rule(component, dimension: str):
    """Deterministic constructive edit for offline coordinator tests."""
    from app.learning.models import Component

    nxt = bump_geo_version(component.version)
    pb = append_us_rule(
        component.playbook or {},
        text=f"Address {dimension} in US-wide appeal norms.",
        version=nxt,
    )
    return Component(
        component_id=component.component_id,
        kind="playbook",
        version=nxt,
        playbook=pb,
    )
