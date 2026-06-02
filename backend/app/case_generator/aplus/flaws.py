"""P4 RealisticFlawInjector — embed pattern IDs from denial_patterns.json."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any


def pattern_source_entries(patterns: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for p in patterns[:3]:
        pid = p.get("id", "unknown_pattern")
        src = p.get("source", "published UM research")
        out.append(f"{pid}: {src}")
    return out or ["ignored_physician_letter: AMA 2023 Prior Authorization Physician Survey"]


def inject_flaws(
    *,
    letter: str,
    context: str,
    brief: dict[str, Any],
    patterns: list[dict[str, Any]],
    index: int,
) -> dict[str, Any]:
    pattern_ids = {p.get("id") for p in patterns}
    letter_out = letter
    notes: list[str] = []

    _iro_external = (
        " If this denial is upheld after internal review, you may have the right to "
        "request an independent external review of our decision at no cost to you, "
        "subject to applicable federal and state requirements."
    )
    if "missing_iro_notice" in pattern_ids or any(
        "iro" in f.lower() for f in brief.get("intended_flaw_types", [])
    ):
        if _iro_external in letter_out:
            letter_out = letter_out.replace(_iro_external, "")
        letter_out = letter_out.replace(
            "You have the right to appeal this determination.",
            "You have the right to appeal this determination through our internal appeals process.",
        )
        notes.append("Suppressed explicit independent external review (IRO) notice.")

    if "missing_erisa_disclosures" in pattern_ids:
        # Leave absent — note only
        notes.append("Omitted ERISA plan-document and civil-action disclosures.")

    if "step_therapy_vague_mcg" in pattern_ids or "superseded_guideline" in pattern_ids:
        letter_out = letter_out.replace(
            "utilization-management requirements",
            "MCG Care Guidelines (edition not specified) and utilization-management requirements",
        )
        notes.append("Inserted vague MCG reference without edition/module.")

    _ignored_boiler = (
        "\n\nStandard criteria apply regardless of information previously sent to the plan."
    )
    if "ignored_physician_letter" in pattern_ids:
        if _ignored_boiler.strip() not in letter_out:
            if (
                "submitted" not in letter_out.lower()
                or "letter of medical necessity" not in letter_out.lower()
            ):
                letter_out += _ignored_boiler
                notes.append("Boilerplate ignores physician letter and submitted records.")

    if "circular_medical_necessity" in pattern_ids:
        letter_out = letter_out.replace(
            "does not demonstrate that the service is medically necessary",
            "does not meet medical necessity criteria because the service is not medically necessary",
        )
        notes.append("Circular medical-necessity phrasing.")

    if "algo_boilerplate_fingerprint" in pattern_ids and index % 7 == 0:
        # Rare — most letters stay case-specific; only some indices
        pass  # we keep case-specific dx/tx in letter by design

    sub_ts = den_ts = None
    if "algo_time_delta" in pattern_ids:
        base = datetime(2026, 3, 10, 14, 0, 0)
        sub_ts = (base).strftime("%Y-%m-%dT%H:%M:%SZ")
        den_ts = (base + timedelta(minutes=2 + (index % 3))).strftime("%Y-%m-%dT%H:%M:%SZ")
        notes.append("Algo time delta: denial 2–4 minutes after submission.")

    if "timeline_violation" in pattern_ids and not sub_ts:
        base = datetime(2026, 2, 1, 9, 0, 0)
        sub_ts = base.strftime("%Y-%m-%dT%H:%M:%SZ")
        den_ts = (base + timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        notes.append("Denial issued well after standard pre-service window.")

    if "peer_to_peer_window_verbal_only" in pattern_ids:
        letter_out = letter_out.replace(
            "timeframe described in your plan materials",
            "verbal timeframe communicated to office staff (not confirmed in this letter)",
        )
        notes.append("P2P window verbal-only flaw.")

    _reviewer_line = "\n\nThis determination was made by Dr. J. Smith, Medical Director."
    if "non_specialist_reviewer" in pattern_ids and _reviewer_line.strip() not in letter_out:
        letter_out += _reviewer_line
        notes.append("Reviewer named without specialty or credentials.")

    return {
        "denial_letter_text": letter_out,
        "clinical_context": context,
        "diagnosis": brief["diagnosis"],
        "treatment_requested": brief["treatment_requested"],
        "submission_timestamp": sub_ts,
        "denial_timestamp": den_ts,
        "denial_pattern_sources": pattern_source_entries(patterns),
        "perturbation_notes": " ".join(notes) or "Procedural vagueness and disclosure gaps.",
    }


def verify_flaws_present(letter: str, pattern_ids: list[str], sub_ts: str | None, den_ts: str | None) -> list[str]:
    """Return list of missing pattern ids (for internal QA)."""
    missing: list[str] = []
    low = letter.lower()
    for pid in pattern_ids:
        if pid == "missing_iro_notice":
            if "external review" in low or "independent review" in low and "internal" not in low:
                missing.append(pid)
        elif pid == "ignored_physician_letter":
            if "letter of medical necessity" in low or "submitted clinical" in low:
                missing.append(pid)
        elif pid == "step_therapy_vague_mcg":
            if "mcg" not in low and "milliman" not in low:
                missing.append(pid)
        elif pid == "algo_time_delta":
            if not sub_ts or not den_ts:
                missing.append(pid)
            else:
                try:
                    a = datetime.fromisoformat(sub_ts.replace("Z", "+00:00"))
                    b = datetime.fromisoformat(den_ts.replace("Z", "+00:00"))
                    delta = (b - a).total_seconds()
                    if not (60 <= delta <= 300):
                        missing.append(pid)
                except ValueError:
                    missing.append(pid)
        elif pid == "circular_medical_necessity":
            if "not medically necessary because" not in low:
                missing.append(pid)
    return missing
