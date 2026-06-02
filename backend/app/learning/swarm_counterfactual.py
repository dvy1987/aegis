"""Swarm Phoenix-MCP counterfactual — measures load-bearing memory on full pipeline letters.

Runs each benchmark case twice (MCP-enabled vs disabled Phoenix lookup), scores both
via the judge panel, and reports the composite delta. Offline-testable with stubs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from app.aegis_swarm.tools import swarm_phoenix_lookup
from app.evals.part_a.recorder import InMemoryPhoenixRecorder
from app.evals.swarm.evaluated_swarm_run import run_evaluated_swarm_case
from app.learning.models import composite_score

if TYPE_CHECKING:
    from app.aegis_swarm.client import SwarmAgentClient
    from app.aegis_swarm.corpus_store import CorpusStore
    from app.evals.part_a.llm_judges import JudgeClient


def phoenix_lookup_for_mcp_enabled(enabled: bool) -> Callable[[str, str, str], dict[str, Any]]:
    """Return a lookup that forces Phoenix MCP on (cold-start path) or off (disabled)."""

    def _lookup(insurer: str, denial_type: str, case_id: str = "interactive_case") -> dict[str, Any]:
        import os

        prior = os.environ.get("PHOENIX_MCP_ENABLED")
        os.environ["PHOENIX_MCP_ENABLED"] = "true" if enabled else "false"
        try:
            return swarm_phoenix_lookup(insurer, denial_type, case_id)
        finally:
            if prior is None:
                os.environ.pop("PHOENIX_MCP_ENABLED", None)
            else:
                os.environ["PHOENIX_MCP_ENABLED"] = prior

    return _lookup


def run_swarm_counterfactual(
    cases: list[dict[str, Any]],
    *,
    swarm_client: "SwarmAgentClient | None" = None,
    judge_client: "JudgeClient | None" = None,
    corpus_store: "CorpusStore | None" = None,
    lookup_on: Callable[[str, str, str], dict[str, Any]] | None = None,
    lookup_off: Callable[[str, str, str], dict[str, Any]] | None = None,
    run_simulator: bool = False,
) -> dict[str, Any]:
    """Draft each case with Phoenix MCP on vs off; score both; aggregate composite delta."""
    on_lookup = lookup_on or phoenix_lookup_for_mcp_enabled(True)
    off_lookup = lookup_off or phoenix_lookup_for_mcp_enabled(False)
    per_case: list[dict[str, Any]] = []

    for case in cases:
        rec_on = InMemoryPhoenixRecorder()
        rec_off = InMemoryPhoenixRecorder()
        run_on = run_evaluated_swarm_case(
            case,
            rec_on,
            swarm_client=swarm_client,
            judge_client=judge_client,
            corpus_store=corpus_store,
            run_simulator=run_simulator,
            phoenix_lookup=on_lookup,
        )
        run_off = run_evaluated_swarm_case(
            case,
            rec_off,
            swarm_client=swarm_client,
            judge_client=judge_client,
            corpus_store=corpus_store,
            run_simulator=run_simulator,
            phoenix_lookup=off_lookup,
        )
        s_on = run_on.panel_report
        s_off = run_off.panel_report
        c_on = composite_score(s_on.dimension_scores, s_on.verdict == "PASS")
        c_off = composite_score(s_off.dimension_scores, s_off.verdict == "PASS")
        insurer_on = run_on.artifacts.get("insurer_brief") or {}
        insurer_off = run_off.artifacts.get("insurer_brief") or {}
        per_case.append(
            {
                "case_id": case.get("case_id", ""),
                "on": c_on,
                "off": c_off,
                "delta": round(c_on - c_off, 4),
                "phoenix_memory_active_on": "phoenix_mcp_unavailable"
                not in (insurer_on.get("risk_flags") or []),
                "phoenix_memory_degraded_off": "phoenix_mcp_unavailable"
                in (insurer_off.get("risk_flags") or []),
            }
        )

    n = len(per_case)
    on_mean = round(sum(p["on"] for p in per_case) / n, 4) if n else 0.0
    off_mean = round(sum(p["off"] for p in per_case) / n, 4) if n else 0.0
    return {
        "on_composite": on_mean,
        "off_composite": off_mean,
        "delta": round(on_mean - off_mean, 4),
        "per_case": per_case,
    }
