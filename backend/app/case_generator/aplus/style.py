"""P5 StylisticDiversifier — minimal edits preserving flaws."""

from __future__ import annotations

from typing import Any


def diversify(stylized_in: dict[str, Any], index: int, neighbour_summaries: list[str]) -> dict[str, Any]:
    letter = stylized_in["denial_letter_text"]
    ctx = stylized_in["clinical_context"]

    # Avoid copying neighbour openers
    if neighbour_summaries and "Dear Member," in letter:
        if index % 4 == 1:
            letter = letter.replace("Dear Member,", "Dear Plan Member,", 1)
        elif index % 4 == 2:
            letter = letter.replace(
                "We received your provider's request",
                "This letter advises you of our determination regarding your provider's request",
                1,
            )

    # Grounding detail in clinical context (P5 lever)
    if "PHQ-9" not in ctx and index % 5 == 0:
        ctx = ctx.replace(
            "objective findings",
            "objective findings (including dated scale scores in the chart)",
            1,
        )
    elif "weeks" not in ctx and "mg" in ctx:
        pass
    else:
        # Add quarter reference once
        if "Q1 2026" not in ctx and "2025" not in ctx:
            ctx = ctx.replace(
                "original request",
                "original request submitted in Q1 2026",
                1,
            )

    return {
        **stylized_in,
        "denial_letter_text": letter,
        "clinical_context": ctx,
        "stylistic_notes": f"Applied index-based opener/clinical grounding levers (index {index}).",
    }
