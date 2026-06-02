from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.case_generator.validator import validate_case

from .arbiter import arbitrate
from .critics import (
    clinical_critic,
    contradiction_hunter,
    demographic_validator,
    diagnosis_treatment_match,
    flaw_injection_verifier,
    llm_tell_detector,
    safety_redactor,
    scope_guard,
    tone_critic,
)
from .fixes import apply_safe_fixes
from .types import GumloopRunResult


def run_swarm_once(case: dict[str, Any]) -> GumloopRunResult:
    case_id = str(case.get("case_id") or "")

    # Tier 1 hard gates
    tier1 = {
        "contradiction_hunter": contradiction_hunter(case),
        "scope_guard": scope_guard(case),
        "safety_redactor": safety_redactor(case),
        "dx_tx_match": diagnosis_treatment_match(case),
        "demographic_validator": demographic_validator(case),
    }

    # Tier 2 realism critics (offline subset)
    tier2 = {
        "flaw_injection_verifier": flaw_injection_verifier(case),
        "clinical_critic": clinical_critic(case),
        "tone_critic": tone_critic(case),
        "tell_detector": llm_tell_detector(case),
    }

    arb = arbitrate(case_id=case_id, tier1=tier1, tier2=tier2)
    critic_outputs = {**tier1, **tier2}
    return GumloopRunResult(case_id=case_id, arbiter=arb, critic_outputs=critic_outputs)


def run_pass_on_case(case: dict[str, Any], *, max_fix_iters: int = 2) -> tuple[dict[str, Any], list[GumloopRunResult]]:
    """Run swarm; if REVISE, apply safe fixes and re-run (bounded)."""
    history: list[GumloopRunResult] = []
    cur = case
    for _ in range(max_fix_iters + 1):
        res = run_swarm_once(cur)
        history.append(res)
        # Special-case: if the only Tier 1 failure is demographics, attempt a safe normalization and retry.
        if res.arbiter["verdict"] == "DISCARD" and res.arbiter.get("tier_1_failures") == ["demographic_validator"]:
            cur = apply_safe_fixes(cur)
            continue
        if res.arbiter["verdict"] != "REVISE":
            break
        cur = apply_safe_fixes(cur)
    return cur, history


def run_pass_on_drafts(
    *,
    drafts_dir: Path,
    out_report_path: Path,
    apply_fixes: bool = True,
    max_fix_iters: int = 2,
) -> dict[str, Any]:
    """Run the offline Gumloop pass over `eval/cases/drafts/case_*.json`.

    - Does NOT move anything to `approved/`.
    - Writes a JSONL report containing arbiter + critics per case per iteration.
    - If `apply_fixes` is True, writes back fixed cases in-place.
    """
    paths = sorted(drafts_dir.glob("case_*.json"))
    out_report_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "total": 0,
        "final_verdict_counts": {"APPROVE": 0, "REVISE": 0, "DISCARD": 0},
        "schema_failures": 0,
        "cases": [],
    }

    with out_report_path.open("w", encoding="utf-8") as f:
        for p in paths:
            case = json.loads(p.read_text(encoding="utf-8"))
            summary["total"] += 1

            final_case = case
            history: list[GumloopRunResult] = []
            if apply_fixes:
                final_case, history = run_pass_on_case(case, max_fix_iters=max_fix_iters)
            else:
                history = [run_swarm_once(case)]

            # Validate before writing changes.
            vr = validate_case(final_case)
            if not vr.ok:
                summary["schema_failures"] += 1

            if apply_fixes and vr.ok and final_case != case:
                p.write_text(json.dumps(final_case, indent=2), encoding="utf-8")

            final_verdict = history[-1].arbiter["verdict"]
            summary["final_verdict_counts"][final_verdict] += 1
            summary["cases"].append(
                {
                    "case_id": final_case.get("case_id"),
                    "path": str(p),
                    "final_verdict": final_verdict,
                    "iters": len(history),
                    "tier_1_failures": history[-1].arbiter["tier_1_failures"],
                    "tier_2_failures": history[-1].arbiter["tier_2_failures"],
                }
            )

            for i, h in enumerate(history):
                f.write(json.dumps({"iter": i, **asdict(h)}, ensure_ascii=False) + "\n")

    return summary

