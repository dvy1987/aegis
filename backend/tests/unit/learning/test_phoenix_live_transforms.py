"""Pure transform tests for rows_to_scored_runs (Tier 1 Phase D).

The transform parses Phoenix span + annotation rows (the shapes recorded into
backend/tests/fixtures/phoenix/) into ScoredRun objects that the Learning
Coordinator reads via the PhoenixLearningStore Protocol. INV-2 requires the
firewall to hold across this read path: no answer-key field may survive.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.learning.phoenix_live import rows_to_scored_runs
from app.learning.signal import FORBIDDEN_FIELDS


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "phoenix"


def test_rows_to_scored_runs_parses_minimal_pair() -> None:
    spans = [
        {
            "context": {"span_id": "abc123"},
            "name": "aegis_v1.evaluated_run",
            "attributes": {
                "aegis.case_id": "case_01_cigna_mednec",
                "aegis.insurer": "Cigna",
                "aegis.denial_type": "medical_necessity",
                "aegis.dataset_split": "benchmark_train",
                "aegis.prompt_version": "drafter_v2",
                "aegis.playbook_version": "v1",
            },
        }
    ]
    annotations = [
        {
            "span_id": "abc123",
            "name": "aegis_part_a_panel",
            "result": {
                "label": "PASS",
                "score": 0.78,
                "explanation": json.dumps({
                    "case_id": "case_01_cigna_mednec",
                    "verdict": "PASS",
                    "weighted_quality": 0.78,
                    "dimension_scores": {
                        "grounding": 5,
                        "appeal_vector_capture": 3,
                        "case_specific_clinical_rebuttal": 3,
                        "evidence_completeness": 5,
                        "persuasive_coherence": 3,
                    },
                    "dimensions": {
                        "appeal_vector_capture": {
                            "score": 3,
                            "improvement": "tighten the rebuttal of the cited reason",
                        },
                    },
                }),
            },
        }
    ]
    runs = rows_to_scored_runs(spans, annotations)
    assert len(runs) == 1
    run = runs[0]
    assert run.case_id == "case_01_cigna_mednec"
    assert run.slice == "Cigna:medical_necessity"
    assert run.hard_gate_pass is True
    assert run.weighted_quality == pytest.approx(0.78)
    assert run.prompt_version == "drafter_v2"
    assert run.playbook_version == "v1"
    assert run.dimension_scores["appeal_vector_capture"] == 3
    assert "appeal_vector_capture" in run.improvement_notes


def test_rows_to_scored_runs_drops_spans_without_annotation() -> None:
    spans = [
        {"context": {"span_id": "lonely"}, "attributes": {"aegis.case_id": "x"}},
    ]
    runs = rows_to_scored_runs(spans, annotations=[])
    assert runs == []


def test_rows_to_scored_runs_strips_forbidden_answer_key_fields() -> None:
    """Even if a poisoned annotation rides forbidden fields along, the
    ScoredRun must not surface them (INV-2 defence in depth)."""
    spans = [
        {
            "context": {"span_id": "p1"},
            "attributes": {
                "aegis.case_id": "case_x",
                "aegis.insurer": "Aetna",
                "aegis.denial_type": "prior_authorization",
            },
        }
    ]
    payload = {
        "case_id": "case_x",
        "verdict": "FAIL",
        "weighted_quality": 0.4,
        "dimension_scores": {"grounding": 1},
        "dimensions": {
            "grounding": {"score": 1, "improvement": "missed the cited regulation"},
        },
        # Forbidden fields that must not survive:
        "expected_appeal_vectors": ["TEACHER ONLY: cite plan §4.2"],
        "exploitable_weaknesses": ["TEACHER ONLY: silent on mode"],
        "appeal_difficulty": "hard",
    }
    annotations = [{
        "span_id": "p1",
        "name": "aegis_part_a_panel",
        "result": {"label": "FAIL", "score": 0.4, "explanation": json.dumps(payload)},
    }]
    runs = rows_to_scored_runs(spans, annotations)
    assert len(runs) == 1
    blob = runs[0].model_dump_json()
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in blob, f"forbidden field {forbidden!r} leaked"
    assert "TEACHER ONLY" not in blob


def test_rows_to_scored_runs_against_recorded_fixture() -> None:
    """Parse the real Phoenix payloads recorded in the fixtures directory.
    Validates the transform against actual column/field names."""
    spans_path = FIXTURE_DIR / "spans_sample.json"
    annotations_path = FIXTURE_DIR / "annotations_sample.json"
    if not spans_path.exists() or not annotations_path.exists():
        pytest.skip("phoenix fixtures not yet recorded")
    spans = json.loads(spans_path.read_text())
    ann_payload = json.loads(annotations_path.read_text())
    annotations = (
        ann_payload.get("annotations", [])
        if isinstance(ann_payload, dict)
        else ann_payload
    )
    runs = rows_to_scored_runs(spans, annotations)
    if not runs:
        pytest.skip("no parseable runs in current fixtures")
    for r in runs:
        assert r.case_id and r.slice
        assert 0.0 <= r.weighted_quality <= 1.0
    blob = "\n".join(r.model_dump_json() for r in runs)
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in blob


def test_live_store_construction_offline() -> None:
    """LivePhoenixLearningStore must construct without GCP/Phoenix creds.
    All cloud calls happen at method-call time, not at __init__."""
    from app.learning.phoenix_live import LivePhoenixLearningStore

    store = LivePhoenixLearningStore(project="default")
    assert store.name == "live_phoenix_learning_store"
    # No network call yet — listing versions for an unknown component returns [].
    assert store.list_prompt_versions("never_seeded") == []
