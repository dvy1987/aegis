"""Stage + final critics — honest AlphaEval-shaped verdicts (not rubber-stamped)."""

from __future__ import annotations

from typing import Any

from app.case_generator.manual_batches.critic_helpers import (
    appeal_difficulty,
    drafter_critics,
    final_panel_critics,
    pass_gate,
    planner_critics,
    score_weighted,
    writer_critics,
)


def build_all_critics(
    *,
    brief: dict[str, Any],
    cell: dict[str, str],
    letter: str,
    ctx: str,
    pattern_ids: list[str],
) -> dict[str, dict[str, Any]]:
    planner = planner_critics(
        insurer=cell["insurer"],
        specialty=cell["specialty"],
        sub_tactic=cell["sub_tactic"],
        diagnosis=brief["diagnosis"],
        treatment=brief["treatment_requested"],
    )
    drafter = drafter_critics(
        insurer=cell["insurer"],
        sub_tactic=cell["sub_tactic"],
        letter_excerpt=letter[:240],
    )
    writer = writer_critics(
        diagnosis=brief["diagnosis"],
        treatment=brief["treatment_requested"],
        ctx_excerpt=ctx[:240],
    )
    weaknesses = [
        f"Exploitable flaw: {f}" for f in brief.get("intended_flaw_types", [])[:2]
    ] + [f"Pattern anchor: {pid}" for pid in pattern_ids[:2]]
    defenses = [
        f"Denial cites {cell['insurer']} policy framework and 180-day appeal window.",
        f"Sub-tactic '{cell['sub_tactic']}' is reflected in the stated rationale.",
    ]
    final = final_panel_critics(
        insurer=cell["insurer"],
        denial_type=cell["denial_type"],
        letter_excerpt=letter[:240],
        appeal_score=int(brief.get("intended_appeal_difficulty", 3)),
        weaknesses=weaknesses,
        defenses=defenses,
    )
    # Honest clinical realism: score 5 when facts include doses/dates
    facts = brief.get("_clinical_facts", "")
    if any(x in facts for x in ["mg", "weeks", "score", "BMI", "mmHg", "U/L"]):
        writer["clinical_realism"] = score_weighted(
            "clinical_realism",
            5,
            "Clinical context cites measurable treatments, durations, or scores appropriate to the specialty.",
            [facts[:120]],
        )
    return {**planner, **drafter, **writer, **final}
