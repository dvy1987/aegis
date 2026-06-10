"""Bridge swarm eval output to ``ScoredRun`` for the Learning Coordinator."""

from __future__ import annotations

from typing import Any

from app.evals.part_a.schemas import PanelReport
from app.learning.models import ScoredRun, composite_score


def _case_slice(case: dict[str, Any]) -> str:
    from app.learning.slice_key import format_slice_key, sub_tactic_from_case

    insurer = case.get("insurer") or case.get("patient_profile", {}).get("insurer", "unknown")
    denial = case.get("denial_type") or "unknown"
    return format_slice_key(str(insurer), str(denial), sub_tactic_from_case(case))


def _launder_trace_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only firewall-safe trace fields (INV-2)."""
    allowed = {
        "role", "prompt_version", "is_weak_v1", "owned_dimensions", "status",
        "finding_count", "citation_count", "risk_flags", "summary",
    }
    out: list[dict[str, Any]] = []
    for sig in signals:
        out.append({k: sig[k] for k in allowed if k in sig})
    return out


def panel_to_scored_run(
    *,
    case: dict[str, Any],
    panel: PanelReport,
    agent_versions: dict[str, str] | None = None,
    trace_signals: list[dict[str, Any]] | None = None,
    simulator_verdict: str | None = None,
) -> ScoredRun:
    dims = {k: int(v) for k, v in panel.dimension_scores.items()}
    gate = panel.verdict == "PASS"
    wq = panel.weighted_quality
    if wq is None:
        wq = composite_score(dims, gate)
    notes = {
        name: (result.improvement or "")
        for name, result in panel.judge_results.items()
        if result.improvement
    }
    versions = agent_versions or {}
    return ScoredRun(
        case_id=case.get("case_id", "unknown"),
        slice=_case_slice(case),
        dimension_scores=dims,
        hard_gate_pass=gate,
        weighted_quality=float(wq),
        improvement_notes=notes,
        simulator_verdict=simulator_verdict,  # type: ignore[arg-type]
        prompt_version=",".join(f"{k}:{v}" for k, v in sorted(versions.items())),
        swarm_trace_signals=_launder_trace_signals(trace_signals or []),
    )
