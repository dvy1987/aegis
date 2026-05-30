from __future__ import annotations

from typing import Any, Protocol

from app.evals.part_a.schemas import PanelReport


def laundered_signal(panel: PanelReport, appeal_letter: str) -> dict[str, Any]:
    """Firewall-safe projection of a PanelReport for the Optimizer (INV-2).

    Keeps scores, gates, reasoning, improvement notes. Keeps an evidence quote
    ONLY if it appears verbatim in the agent's own letter — so teacher-only
    answer-key strings (e.g. expected appeal vectors) can never leak.
    """
    letter = appeal_letter or ""
    dimensions: dict[str, Any] = {}
    for name, result in panel.judge_results.items():
        safe_quotes = [q for q in result.evidence_quotes if q and q in letter]
        dimensions[name] = {
            "score": result.score,
            "reasoning": result.reasoning,
            "improvement": result.improvement,
            "evidence_quotes": safe_quotes,
        }
    return {
        "case_id": panel.case_id,
        "verdict": panel.verdict,
        "weighted_quality": panel.weighted_quality,
        "hard_gate_failures": panel.hard_gate_failures,
        "promotion_blockers": panel.promotion_blockers,
        "dimension_scores": panel.dimension_scores,
        "weights": panel.weights,
        "dimensions": dimensions,
    }


class PhoenixRecorder(Protocol):
    name: str

    def record_run(self, appeal_package: dict[str, Any], trace_metadata: dict[str, Any]) -> str:
        """Persist one run; return a trace reference (e.g. span/trace id)."""

    def annotate(self, trace_ref: str, annotations: dict[str, Any]) -> None:
        """Attach laundered eval/sim signal to an existing run."""


class InMemoryPhoenixRecorder:
    """Offline fake implementing the PhoenixRecorder interface for tests/dry-runs."""

    name = "in_memory"

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._seq = 0

    def record_run(self, appeal_package, trace_metadata) -> str:
        self._seq += 1
        ref = f"mem-trace-{self._seq}"
        self._runs[ref] = {
            "appeal_package": appeal_package,
            "metadata": dict(trace_metadata),
            "annotations": {},
        }
        return ref

    def annotate(self, trace_ref, annotations) -> None:
        self._runs[trace_ref]["annotations"].update(annotations)

    def get(self, trace_ref: str) -> dict[str, Any]:
        return self._runs[trace_ref]
