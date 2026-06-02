"""Material denial-letter improvements informed by web-research sources (in-place upgrades)."""

from __future__ import annotations

import re
from typing import Any

from .text_metrics import fit_letter_word_budget, repair_denial_letter_artifacts

_CLAIM_FILE_BLOCK = (
    "\n\nYOUR RIGHT TO INFORMATION\n"
    "You may request a copy of your claim file and the clinical criteria we used "
    "in this determination. Submit your request to the address on this notice or "
    "through your plan's member portal."
)

_P2P_BY_INSURER = {
    "Aetna": (
        "Your treating physician may request a peer-to-peer discussion with an "
        "Aetna medical director before filing a written appeal."
    ),
    "Cigna": (
        "Your treating physician may request a peer-to-peer discussion with a Cigna "
        "medical director regarding this determination."
    ),
    "UHC": (
        "Your treating physician may request a peer-to-peer discussion with a "
        "UnitedHealthcare medical director before initiating a formal appeal on "
        "the same authorization decision."
    ),
}

_UM_VENDOR_LINE = (
    "This review used clinical criteria from our designated utilization-management "
    "program; the criteria document is available upon request."
)


def parse_pattern_ids(denial_pattern_sources: list[str]) -> list[str]:
    ids: list[str] = []
    for entry in denial_pattern_sources:
        if ":" in entry:
            ids.append(entry.split(":", 1)[0].strip())
        elif entry.strip():
            ids.append(entry.strip())
    return ids


def _insert_before_appeal_rights(letter: str, block: str) -> str:
    if "\n\nAPPEAL RIGHTS" in letter:
        return letter.replace("\n\nAPPEAL RIGHTS", block + "\n\nAPPEAL RIGHTS", 1)
    return letter + block


def enhance_denial_letter(
    letter: str,
    *,
    insurer: str,
    denial_type: str,
    cell: dict[str, str],
    pattern_ids: list[str],
    fit_budget: bool = True,
) -> str:
    """Apply non-destructive realism upgrades; flaw injection runs afterward."""
    out = repair_denial_letter_artifacts(letter)
    low = out.lower()

    if "claim file" not in low and "your right to information" not in low:
        out = _insert_before_appeal_rights(out, _CLAIM_FILE_BLOCK)

    if "peer-to-peer" not in low and "peer to peer" not in low:
        if "missing_peer_to_peer" not in pattern_ids:
            p2p = _P2P_BY_INSURER.get(insurer, _P2P_BY_INSURER["Aetna"])
            out = _insert_before_appeal_rights(out, f"\n\n{p2p}")

    if insurer == "Aetna" and "clinical policy bulletin" not in low:
        out = out.replace(
            "Clinical policy applied:",
            "Clinical policy applied (Clinical Policy Bulletin / CPB):",
            1,
        )

    if insurer == "Cigna" and "cpg" not in low and "Coverage Policy" in out:
        out = out.replace(
            "under Cigna Medical Coverage Policy",
            "under Cigna Medical Coverage Policy (CPG)",
            1,
        )

    if insurer == "UHC" and "CDG-UM" in out and "authoritative clinical policy" in low:
        out = out.replace(
            "under UnitedHealthcare Coverage Determination Guideline (CDG; authoritative "
            "clinical policy for this review)",
            "under UnitedHealthcare Coverage Determination Guideline (CDG)",
            1,
        )

    if denial_type == "Prior Authorization":
        if "prior authorization" not in low[:500]:
            out = out.replace(
                "adverse benefit determination.",
                "adverse benefit determination regarding prior authorization.",
                1,
            )

    if any(
        pid in pattern_ids
        for pid in (
            "step_therapy_vague_mcg",
            "superseded_guideline",
            "incorrect_demographic_guideline",
        )
    ):
        if "utilization-management program" not in low and "Diagnosis and procedure codes" in out:
            out = out.replace(
                "Diagnosis and procedure codes",
                _UM_VENDOR_LINE + "\n\nDiagnosis and procedure codes",
                1,
            )

    if "missing_cost_liability" in pattern_ids:
        if "financial responsibility" not in low and "cost-sharing" in low:
            out = out.replace(
                "Please note that benefits are subject to all terms",
                "If you proceed with the service, financial responsibility for non-covered "
                "charges may apply under your plan. Please note that benefits are subject "
                "to all terms",
                1,
            )

    if fit_budget:
        out = fit_letter_word_budget(out)
    return out.strip()
