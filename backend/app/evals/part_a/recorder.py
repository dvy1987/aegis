from __future__ import annotations

import os
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


class OtelPhoenixRecorder:
    """Production recorder: a tagged span per run + Phoenix eval annotations.

    Live span emission and `log_evaluations` are exercised in a GCP integration
    session; this class is unit-tested only for construction/config here.
    """

    name = "otel_phoenix"

    def __init__(self, project_name: str | None = None) -> None:
        self.project_name = project_name or os.environ.get("PHOENIX_PROJECT_NAME", "default")

    def record_run(self, appeal_package, trace_metadata) -> str:
        from opentelemetry import trace as otel_trace

        tracer = otel_trace.get_tracer("aegis.evaluated_run")
        with tracer.start_as_current_span("aegis_v1.evaluated_run") as span:
            for key, value in trace_metadata.items():
                span.set_attribute(f"aegis.{key}", str(value))
            span.set_attribute("aegis.run_id", str(appeal_package.get("run_id", "")))
            ctx = span.get_span_context()
            return format(ctx.span_id, "016x")

    def annotate(self, trace_ref, annotations) -> None:
        import pandas as pd
        from phoenix.client import Client

        # Phoenix Client API changes frequently; the stable surface is
        # span annotations. We log the laundered eval signal as a CODE annotation
        # so it is visible in the UI for demo + debugging.
        verdict = str(annotations.get("verdict", ""))
        weighted = annotations.get("weighted_quality")
        try:
            score = float(weighted) if weighted is not None else 0.0
        except Exception:
            score = 0.0

        explanation = (
            f"verdict={verdict} weighted_quality={weighted} "
            f"hard_gate_failures={annotations.get('hard_gate_failures', [])}"
        )

        df = pd.DataFrame(
            [
                {
                    "label": verdict,
                    "score": score,
                    "explanation": explanation,
                    **annotations,
                }
            ]
        )
        df.index = [trace_ref]
        df.index.name = "span_id"
        try:
            Client().spans.log_span_annotations_dataframe(
                dataframe=df,
                annotator_kind="CODE",
                annotation_name="aegis_part_a_panel",
                sync=True,
            )
        except Exception:
            # Best-effort: recording the span itself is the load-bearing demo artifact.
            # Annotation upload depends on Phoenix client/endpoint wiring and must not
            # fail the product or showcase path.
            return
