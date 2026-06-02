"""Phoenix signal acquisition with credit-map component resolution (swarm)."""

from __future__ import annotations

from app.learning.credit_resolution import resolve_credit_target
from app.learning.models import DIMENSIONS, CorpusGapRecommendation, DimensionSignal
from app.learning.signal import _launder
from app.learning.store import PhoenixLearningStore


def acquire_swarm_signal(
    store: PhoenixLearningStore,
    *,
    dataset_split: str,
    slice_filter: str | None = None,
) -> tuple[DimensionSignal | None, CorpusGapRecommendation | None]:
    """Read train-split runs, resolve the responsible agent via credit map, return signal.

    When ``corpus_gap`` is set, signal is None — queue discovery instead of mutating.
    """
    runs = store.read_scored_runs(dataset_split=dataset_split)
    if slice_filter is not None:
        runs = [r for r in runs if r.slice == slice_filter]
    if not runs:
        return None, None

    resolution = resolve_credit_target(runs)
    if resolution.action == "corpus_gap":
        return None, CorpusGapRecommendation(
            weakest_dimension=resolution.weakest_dimension,
            reason=resolution.corpus_gap_reason,
        )

    component_id = resolution.component_id
    weakest = resolution.weakest_dimension

    dim_means = {
        d: sum(r.dimension_scores.get(d, 1) for r in runs) / len(runs) for d in DIMENSIONS
    }
    notes: dict[str, list[str]] = {d: [] for d in DIMENSIONS}
    for r in runs:
        for dim, note in _launder(r.improvement_notes).items():
            if note:
                notes[dim].append(note)

    failing = [
        r.model_copy(update={"improvement_notes": _launder(r.improvement_notes)})
        for r in runs
        if not r.hard_gate_pass or r.dimension_scores.get(weakest, 1) < 5
    ]
    signal = DimensionSignal(
        component_id=component_id,
        weakest_dimension=weakest,
        failing_cases=failing,
        notes=notes,
    )
    return signal, None
