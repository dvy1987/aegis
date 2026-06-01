"""P2 DenialDrafter — insurer-voice letters (200–500 words)."""

from __future__ import annotations

from typing import Any


def _dates(index: int) -> tuple[str, str, str, str]:
    month = 1 + (index % 10)
    day = 3 + (index % 22)
    year = 2026
    recv = f"{month:02d}/{day:02d}/{year}"
    dec = f"{month:02d}/{day + 18:02d}/{year}"
    return recv, dec, f"{year}-{month:02d}-{day:02d}", f"{year}-{month:02d}-{day + 18:02d}"


def _policy_ref(insurer: str) -> str:
    return {
        "Aetna": "Aetna Clinical Policy Bulletin (CPB) criteria and InterQual review standards",
        "Cigna": "Cigna Medical Coverage Policies and Milliman Care Guidelines (MCG)",
        "UHC": "UnitedHealthcare Medical Management Guidelines and Optum clinical criteria",
    }[insurer]


def _sign(insurer: str) -> str:
    return {
        "Aetna": "Aetna Medical Management",
        "Cigna": "Cigna Health Care Management",
        "UHC": "UnitedHealthcare Utilization Management",
    }[insurer]


def draft_denial_letter(brief: dict[str, Any], cell: dict[str, str], index: int) -> str:
    insurer = cell["insurer"]
    recv, dec, _, _ = _dates(index)
    dx = brief["diagnosis"]
    tx = brief["treatment_requested"]
    policy = _policy_ref(insurer)
    rationale = brief["denial_rationale_seed"]
    employer = brief.get("employer_archetype")
    emp_line = ""
    if employer:
        emp_line = (
            f"\n\nThis determination applies to your employer-sponsored commercial "
            f"benefit while you remain covered under an active group plan ({employer})."
        )

    sub = cell["sub_tactic"].replace("_", " ")
    body = f"""Dear Member,

We received your provider's request on {recv} for {tx} related to {dx}. After review, we cannot approve this request.

Our review applied {policy}. The documentation submitted does not demonstrate that the service is medically necessary for this member at this time. {rationale}

Specifically, the information provided does not satisfy the utilization-management requirements associated with {sub}. The clinical notes reviewed did not include sufficient detail to confirm that plan criteria were met. The requesting provider may submit additional records, but the current file does not support approval.

If your provider wishes to discuss this determination, they may contact our physician review line. Any discussion must occur within the timeframe described in your plan materials.

You have the right to appeal this determination. To file a standard appeal, send a written request and supporting medical records within 180 days of the date of this letter. Include your member identification number and the service reference shown on your explanation of benefits.{emp_line}

Sincerely,

{_sign(insurer)}"""

    # Pad toward 200 words if needed with insurer-appropriate procedural text
    words = body.split()
    if len(words) < 200:
        body += (
            "\n\nPlease note that benefits are subject to all terms, exclusions, and "
            "limitations of your group health plan document. This letter constitutes "
            "the formal adverse determination for the service identified above."
        )
    return body.strip()
