from __future__ import annotations

from app.learning.models import DIMENSIONS, DimensionSignal, ScoredRun
from app.learning.store import PhoenixLearningStore

# Answer-key / teacher-only fields that must NEVER reach the Student or Optimizer (INV-2).
FORBIDDEN_FIELDS = frozenset({
    "expected_appeal_vectors", "exploitable_weaknesses", "appeal_difficulty",
    "synthetic_provenance", "evaluator_disagreements",
})


def _launder(notes: dict[str, str]) -> dict[str, str]:
    """Keep only rubric-dimension keys; drop any answer-key field (defence in depth)."""
    return {k: v for k, v in notes.items() if k in DIMENSIONS and k not in FORBIDDEN_FIELDS}


def acquire_signal(store: PhoenixLearningStore, *, component_id: str, dataset_split: str,
                   slice_filter: str | None) -> DimensionSignal | None:
    """Read the eval signal FROM Phoenix (INV-1) and reduce it to a firewalled
    DimensionSignal for one component: the weakest rubric dimension on this slice and
    the laundered per-dimension improvement notes. Returns None when there is no
    Phoenix signal (the 'Phoenix-off → learning halts' counterfactual)."""
    runs = store.read_scored_runs(dataset_split=dataset_split)
    if slice_filter is not None:
        runs = [r for r in runs if r.slice == slice_filter]
    if not runs:
        return None

    dim_means = {
        d: sum(r.dimension_scores.get(d, 1) for r in runs) / len(runs) for d in DIMENSIONS
    }
    weakest = min(DIMENSIONS, key=lambda d: dim_means[d])

    notes: dict[str, list[str]] = {d: [] for d in DIMENSIONS}
    for r in runs:
        for dim, note in _launder(r.improvement_notes).items():
            if note:
                notes[dim].append(note)

    # Launder improvement_notes on the runs we carry forward too (defence in depth):
    # failing_cases are serialized into the reflection minibatch, so forbidden keys must
    # be stripped here as well, not only in the aggregated `notes` (INV-2).
    failing = [
        r.model_copy(update={"improvement_notes": _launder(r.improvement_notes)})
        for r in runs if not r.hard_gate_pass or r.dimension_scores.get(weakest, 1) < 5
    ]
    return DimensionSignal(component_id=component_id, weakest_dimension=weakest,
                           failing_cases=failing, notes=notes)
