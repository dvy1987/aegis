from __future__ import annotations

from typing import Any

from .types import ArbiterOutput, Verdict


def arbitrate(
    *,
    case_id: str,
    tier1: dict[str, dict[str, Any]],
    tier2: dict[str, dict[str, Any]],
) -> ArbiterOutput:
    """Implements `gumloop/prompts/08_final_arbiter.txt` logic."""
    tier_1_failures: list[str] = []
    for name, out in tier1.items():
        if out.get("verdict") == "FAIL":
            tier_1_failures.append(name)

    if tier_1_failures:
        return {
            "case_id": case_id,
            "evaluator": "Gumloop",
            "verdict": "DISCARD",
            "reason": "Tier 1 hard gate failure (core facts/scope/safety).",
            "tier_1_failures": tier_1_failures,
            "tier_2_failures": [],
            "suggested_revisions": [out.get("improvement") for out in tier1.values() if out.get("improvement")] or [],
        }

    tier_2_failures: list[str] = []
    suggested_revisions: list[str] = []

    # Flaw injection verifier: score 1 => always REVISE.
    fiv = tier2.get("flaw_injection_verifier") or {}
    if fiv.get("score") == 1:
        tier_2_failures.append("flaw_injection_verifier")
        if fiv.get("improvement"):
            suggested_revisions.append(str(fiv["improvement"]))

    # Other Tier 2: score=1 or verdict=FAIL triggers REVISE.
    for name, out in tier2.items():
        if name == "flaw_injection_verifier":
            continue
        if out.get("verdict") == "FAIL" or out.get("score") == 1:
            tier_2_failures.append(name)
            if out.get("improvement"):
                suggested_revisions.append(str(out["improvement"]))

    verdict: Verdict = "APPROVE" if not tier_2_failures else "REVISE"
    reason = (
        "All Tier 1 hard gates passed; no Tier 2 failures."
        if verdict == "APPROVE"
        else "One or more Tier 2 critics flagged revisions needed."
    )
    return {
        "case_id": case_id,
        "evaluator": "Gumloop",
        "verdict": verdict,
        "reason": reason,
        "tier_1_failures": [],
        "tier_2_failures": tier_2_failures,
        "suggested_revisions": suggested_revisions,
    }

