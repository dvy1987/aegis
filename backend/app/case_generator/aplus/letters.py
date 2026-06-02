"""P2 DenialDrafter — insurer-voice letters (200–500 words), ERISA-style surface realism."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .letter_references import select_letter_references

P2_VERSION = "1.1.0"

_PROVIDER_NAMES = (
    "Northline Medical Group",
    "Summit Specialty Associates",
    "Harborview Clinical Partners",
    "Ridgeway Physician Services",
    "Central States Medical Associates",
)


def _dates(index: int) -> tuple[str, str, str]:
    # Keep all notice dates in 2026 even when calibration build_index is 101–120.
    recv_dt = datetime(2026, 1, 5) + timedelta(days=index % 120)
    dos_dt = recv_dt - timedelta(days=2)
    notice_dt = recv_dt + timedelta(days=18)
    return (
        recv_dt.strftime("%m/%d/%Y"),
        notice_dt.strftime("%m/%d/%Y"),
        dos_dt.strftime("%m/%d/%Y"),
    )


def _member_id(index: int) -> str:
    return f"W{100000000 + (index * 7919) % 899999999:09d}"[:10]


def _auth_ref(index: int, denial_type: str) -> str:
    prefix = "PA" if denial_type == "Prior Authorization" else "UM"
    return f"{prefix}-2026-{(index * 137 + 4021) % 900000 + 100000:06d}"


def _claim_ref(index: int) -> str:
    return f"CLM-2026-{(index * 53 + 88001) % 900000 + 100000:06d}"


def _denial_code(denial_type: str) -> tuple[str, str]:
    if denial_type == "Prior Authorization":
        return (
            "CO-197",
            "Precertification/authorization absent — service requires prior approval "
            "before the date of service.",
        )
    return (
        "CO-96",
        "Non-covered charge — service denied as not medically necessary under plan criteria.",
    )


def _policy_block(insurer: str, index: int) -> tuple[str, str]:
    """Return (policy label for narrative, synthetic bulletin id)."""
    n = (index % 40) + 100
    if insurer == "Aetna":
        return (
            "Aetna Clinical Policy Bulletin (CPB) and InterQual® acute-care criteria",
            f"CPB {n:04d}",
        )
    if insurer == "Cigna":
        return (
            "Cigna Medical Coverage Policy and Milliman Care Guidelines (MCG)",
            f"Coverage Policy {n:03d}",
        )
    return (
        "UnitedHealthcare Coverage Determination Guideline (CDG) and applicable "
        "Medical Policy Bulletin",
        f"CDG-UM{n:03d}",
    )


def _plan_name(insurer: str) -> str:
    return {
        "Aetna": "Aetna Choice® POS II (employer-sponsored group health plan)",
        "Cigna": "Cigna Open Access Plus (employer-sponsored group health plan)",
        "UHC": "UnitedHealthcare Choice Plus (employer-sponsored group health plan)",
    }[insurer]


def _sign(insurer: str) -> str:
    return {
        "Aetna": "Aetna Medical Management\nUtilization Management Department",
        "Cigna": "Cigna Health Care Management\nMedical Review Unit",
        "UHC": "UnitedHealthcare Utilization Management\nClinical Operations",
    }[insurer]


def _dx_line(dx: str) -> str:
    """Diagnosis line for case summary — avoid duplicating ICD if already in dx string."""
    if "(" in dx and ")" in dx:
        return dx
    return f"{dx} (ICD-10 per submitted record)"


def draft_denial_letter(
    brief: dict[str, Any],
    cell: dict[str, str],
    index: int,
    *,
    use_web_research: bool = False,
) -> tuple[str, list[dict[str, str]]]:
    """Return (letter_text, denial_letter_references)."""
    insurer = cell["insurer"]
    denial_type = cell["denial_type"]
    recv, notice_date, dos = _dates(index)
    dx = brief["diagnosis"]
    tx = brief["treatment_requested"]
    rationale = brief["denial_rationale_seed"]
    sub = cell["sub_tactic"].replace("_", " ")
    policy_label, bulletin_id = _policy_block(insurer, index)
    code, code_meaning = _denial_code(denial_type)
    member_id = _member_id(index)
    auth_ref = _auth_ref(index, denial_type)
    claim_ref = _claim_ref(index)
    provider = _PROVIDER_NAMES[index % len(_PROVIDER_NAMES)]
    dx_summary = _dx_line(dx)

    pattern_ids = [p.get("id", "") for p in brief.get("_patterns", []) if p.get("id")]
    references = select_letter_references(
        insurer=insurer,
        denial_type=denial_type,
        pattern_ids=pattern_ids,
        cell=cell,
        use_web_research=use_web_research,
    )

    employer = brief.get("employer_archetype")
    emp_line = ""
    if employer:
        emp_line = (
            f"\nFunding: This determination applies under your employer's "
            f"self-funded group arrangement ({employer})."
        )

    request_kind = (
        "prior authorization"
        if denial_type == "Prior Authorization"
        else "precertification / medical necessity review"
    )

    body = f"""NOTICE OF ADVERSE BENEFIT DETERMINATION

Date of Notice: {notice_date}
{_plan_name(insurer)}
Member ID: {member_id}          Group #: GRP-{(index % 9000) + 1000:04d}
Authorization / Reference #: {auth_ref}
Claim #: {claim_ref}
Date of Service (requested): {dos}
Treating provider (as submitted): {provider}

Dear Member,

This document is notice of an adverse benefit determination. We received your provider's {request_kind} request on {recv} for {tx} related to {dx}. After clinical review, we are unable to approve this request.

CASE SUMMARY
Service requested: {tx}
Diagnosis (as submitted): {dx_summary}
Denial code: {code} — {code_meaning}
Clinical policy applied: {bulletin_id} under {policy_label}

EXPLANATION OF DECISION
Our review applied the criteria in {bulletin_id} and your plan's Summary Plan Description (SPD), Section 4 — Medical Benefits and Utilization Management. The documentation submitted does not demonstrate that the service is medically necessary for this member at this time. {rationale}

Specifically, the information provided does not satisfy the utilization-management requirements associated with {sub}. The clinical notes reviewed did not include sufficient detail to confirm that plan criteria were met. The requesting provider may submit additional records, but the current file does not support approval.

Diagnosis and procedure codes used in this determination are available upon request, including plain-language descriptions, as required by applicable federal standards.

If your provider wishes to discuss this determination, they may contact our physician review line. Any discussion must occur within the timeframe described in your plan materials.

APPEAL RIGHTS
You have the right to appeal this determination. If this denial is upheld after internal review, you may have the right to request an independent external review of our decision at no cost to you, subject to applicable federal and state requirements. To file a standard appeal, send a written request and supporting medical records within 180 days of the date of this notice. Include your member identification number ({member_id}) and reference {auth_ref}. You may also have the right to receive, upon request and without charge, copies of documents relevant to this determination.{emp_line}

Please note that benefits are subject to all terms, exclusions, and limitations of your group health plan document. This letter constitutes the formal adverse determination for the service identified above.

Sincerely,

{_sign(insurer)}"""

    words = body.split()
    if len(words) < 200:
        body += (
            "\n\nAdditional plan language regarding experimental/investigational "
            "definitions, network status, and member cost-sharing may apply and "
            "is available upon request."
        )

    return body.strip(), references
