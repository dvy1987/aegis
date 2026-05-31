import pytest

from app.learning.models import ScoredRun, composite_score
from app.learning.signal import FORBIDDEN_FIELDS, acquire_signal
from app.learning.store import InMemoryPhoenixLearningStore


def _run(case_id, scores, notes):
    return ScoredRun(case_id=case_id, slice="Cigna:medical_necessity", dimension_scores=scores,
                     hard_gate_pass=True, weighted_quality=composite_score(scores, True),
                     improvement_notes=notes)


def _store_with_runs():
    store = InMemoryPhoenixLearningStore()
    store.add_run("benchmark_train", _run("a", {"grounding": 5, "appeal_vector_capture": 1},
                  {"appeal_vector_capture": "did not hunt the denial's specific defect"}))
    store.add_run("benchmark_train", _run("b", {"grounding": 5, "appeal_vector_capture": 1},
                  {"appeal_vector_capture": "generic appeal, missed the flaw"}))
    return store


def test_signal_picks_weakest_dimension_and_collects_notes():
    sig = acquire_signal(_store_with_runs(), component_id="playbook:Cigna:medical_necessity",
                         dataset_split="benchmark_train", slice_filter="Cigna:medical_necessity")
    assert sig is not None
    assert sig.weakest_dimension == "appeal_vector_capture"
    assert len(sig.notes["appeal_vector_capture"]) == 2


def test_signal_is_none_when_phoenix_has_no_runs():
    empty = InMemoryPhoenixLearningStore()
    sig = acquire_signal(empty, component_id="drafter_system_prompt",
                         dataset_split="benchmark_train", slice_filter=None)
    assert sig is None   # INV-1: no Phoenix signal -> no gradient


def test_signal_never_exposes_answer_key_fields():
    # Even if a malformed run smuggled answer-key keys into notes, the firewall strips them.
    store = InMemoryPhoenixLearningStore()
    store.add_run("benchmark_train", _run("a", {"appeal_vector_capture": 1},
                  {"appeal_vector_capture": "fine", "exploitable_weaknesses": "LEAK", "appeal_difficulty": "hard"}))
    sig = acquire_signal(store, component_id="playbook:Cigna:medical_necessity",
                         dataset_split="benchmark_train", slice_filter="Cigna:medical_necessity")
    blob = sig.model_dump_json()
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in blob
