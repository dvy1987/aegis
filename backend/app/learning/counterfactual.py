"""MCP-off counterfactual harness — the submission's headline demo.

Thesis: Phoenix MCP is structurally load-bearing — disable it and quality drops. This
measures it: draft each case twice (with the live Phoenix-memory summary vs the
`disabled` summary), score both via the judge adapter, and report the composite delta.

Pure over injected callables, so it is fully offline-testable with fakes; the live demo
passes the real `phoenix_mcp_lookup` with `PHOENIX_MCP_ENABLED` true vs false as the two
lookups, and a PanelJudgeAdapter(GeminiJudgeClient) as the judge.
"""
from __future__ import annotations

from typing import Any, Callable

from app.learning.models import composite_score

Drafter = Callable[[dict[str, Any], dict[str, Any]], str]   # (case, phoenix_summary) -> letter
Lookup = Callable[[dict[str, Any]], dict[str, Any]]          # case -> phoenix_summary


def run_counterfactual(cases: list[dict[str, Any]], *, drafter: Drafter, judge_adapter: Any,
                       lookup_on: Lookup, lookup_off: Lookup) -> dict[str, Any]:
    """For each case, draft with Phoenix MCP on vs off, score both, and aggregate the
    composite delta. `judge_adapter` exposes .score(case=, appeal_letter=) -> {dimension_scores,
    hard_gate_pass} (e.g. PanelJudgeAdapter)."""
    per_case: list[dict[str, Any]] = []
    for case in cases:
        letter_on = drafter(case, lookup_on(case))
        letter_off = drafter(case, lookup_off(case))
        s_on = judge_adapter.score(case=case, appeal_letter=letter_on)
        s_off = judge_adapter.score(case=case, appeal_letter=letter_off)
        c_on = composite_score(s_on["dimension_scores"], s_on["hard_gate_pass"])
        c_off = composite_score(s_off["dimension_scores"], s_off["hard_gate_pass"])
        per_case.append({"case_id": case.get("case_id", ""), "on": c_on, "off": c_off,
                         "delta": round(c_on - c_off, 4)})

    n = len(per_case)
    on_mean = round(sum(p["on"] for p in per_case) / n, 4) if n else 0.0
    off_mean = round(sum(p["off"] for p in per_case) / n, 4) if n else 0.0
    return {"on_composite": on_mean, "off_composite": off_mean,
            "delta": round(on_mean - off_mean, 4), "per_case": per_case}
