"""Pure transform tests for `_summarize_traces` (Tier 1 Phase C).

The transform takes laundered Phoenix trace records (the JSON payload stored
in `aegis_part_a_panel.explanation` plus the `aegis.*` span attributes) and
produces a `PhoenixSummary` for the runtime drafter. The test pins the real
fixture shape recorded from Phoenix project `default`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.aegis_v1.tools import _summarize_traces


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "phoenix"


def test_summary_empty_traces_returns_cold_start() -> None:
    s = _summarize_traces(
        [], insurer="Cigna", denial_type="medical_necessity", query="q"
    )
    assert s.status == "cold_start"
    assert s.similar_trace_count == 0
    assert "phoenix_mcp_cold_start" in s.risk_flags


def test_summary_marks_available_with_failure_patterns_and_success_traits() -> None:
    traces = [
        {
            "verdict": "PASS",
            "weighted_quality": 0.81,
            "dimensions": {
                "appeal_vector_capture": {"score": 5, "improvement": ""},
                "question_agent": {"score": 5, "improvement": ""},
            },
        },
        {
            "verdict": "FAIL",
            "weighted_quality": 0.42,
            "dimensions": {
                "appeal_vector_capture": {
                    "score": 1,
                    "improvement": "did not rebut the specific stated flaw",
                },
                "case_specific_clinical_rebuttal": {
                    "score": 1,
                    "improvement": "missed the trial-of-conservative-care argument",
                },
            },
        },
    ]
    s = _summarize_traces(
        traces, insurer="Cigna", denial_type="medical_necessity", query="q"
    )
    assert s.status == "available"
    assert s.similar_trace_count == 2
    assert s.failure_patterns
    assert any("did not rebut" in fp for fp in s.failure_patterns)
    assert any("strong" in trait for trait in s.success_traits)
    assert "phoenix_mcp_live" in s.risk_flags


def test_summary_dedupes_repeated_failure_patterns() -> None:
    traces = [
        {
            "verdict": "FAIL",
            "weighted_quality": 0.4,
            "dimensions": {
                "appeal_vector_capture": {"score": 1, "improvement": "same note"},
            },
        },
        {
            "verdict": "FAIL",
            "weighted_quality": 0.4,
            "dimensions": {
                "appeal_vector_capture": {"score": 1, "improvement": "same note"},
            },
        },
    ]
    s = _summarize_traces(
        traces, insurer="Cigna", denial_type="medical_necessity", query="q"
    )
    assert s.failure_patterns.count("same note") == 1


def test_summary_caps_returned_patterns_and_traits_at_five() -> None:
    traces = []
    for i in range(8):
        traces.append({
            "verdict": "FAIL",
            "weighted_quality": 0.3,
            "dimensions": {
                "appeal_vector_capture": {"score": 1, "improvement": f"pattern {i}"},
            },
        })
    for i in range(8):
        traces.append({
            "verdict": "PASS",
            "weighted_quality": 0.9,
            "dimensions": {
                "question_agent": {"score": 5, "improvement": ""},
            },
        })
    s = _summarize_traces(
        traces, insurer="Cigna", denial_type="medical_necessity", query="q"
    )
    assert len(s.failure_patterns) <= 5
    assert len(s.success_traits) <= 5


def test_summary_ignores_intermediate_score_three() -> None:
    traces = [
        {
            "verdict": "PASS",
            "weighted_quality": 0.7,
            "dimensions": {
                "appeal_vector_capture": {"score": 3, "improvement": "could be tighter"},
            },
        }
    ]
    s = _summarize_traces(
        traces, insurer="Cigna", denial_type="medical_necessity", query="q"
    )
    assert s.failure_patterns == []
    assert s.success_traits == []


def test_summary_does_not_leak_answer_key_fields() -> None:
    """INV-2: even if a forbidden field somehow rides along on a trace, the
    summary projection must not expose it."""
    traces = [
        {
            "verdict": "PASS",
            "weighted_quality": 0.8,
            "dimensions": {
                "appeal_vector_capture": {"score": 5, "improvement": ""},
            },
            "expected_appeal_vectors": ["TEACHER ONLY: cite InterQual 2026 §4.2"],
            "exploitable_weaknesses": ["TEACHER ONLY: silent on trial-of-care"],
        }
    ]
    s = _summarize_traces(
        traces, insurer="Cigna", denial_type="medical_necessity", query="q"
    )
    blob = s.model_dump_json()
    assert "expected_appeal_vectors" not in blob
    assert "exploitable_weaknesses" not in blob
    assert "TEACHER ONLY" not in blob


def test_summary_parses_recorded_fixture_explanations() -> None:
    """The recorded fixture stores the laundered payload as a JSON string in
    `result.explanation`. The transform must parse those back into trace dicts
    and produce an `available` summary."""
    annotations_path = FIXTURE_DIR / "annotations_sample.json"
    if not annotations_path.exists():
        pytest.skip("phoenix fixtures not yet recorded")
    payload = json.loads(annotations_path.read_text())
    items = payload.get("annotations", []) if isinstance(payload, dict) else payload
    traces: list[dict] = []
    for ann in items:
        if not isinstance(ann, dict):
            continue
        if ann.get("name") != "aegis_part_a_panel":
            continue
        explanation = (ann.get("result") or {}).get("explanation") or ""
        try:
            parsed = json.loads(explanation)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "dimensions" in parsed:
            traces.append(parsed)

    if not traces:
        pytest.skip("fixture has no parseable laundered annotations yet")

    s = _summarize_traces(
        traces, insurer="Cigna", denial_type="medical_necessity", query="q"
    )
    assert s.status == "available"
    assert s.similar_trace_count == len(traces)
