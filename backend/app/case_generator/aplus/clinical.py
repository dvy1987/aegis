"""P3 ClinicalContextWriter — case-specific rebuttal (80–250 words)."""

from __future__ import annotations

from typing import Any


def draft_clinical_context(brief: dict[str, Any], cell: dict[str, str]) -> str:
    age = brief["patient_age"]
    gender = brief["patient_gender"]
    pronoun = "She" if gender == "F" else "He" if gender == "M" else "They"
    possessive = "her" if gender == "F" else "his" if gender == "M" else "their"
    facts = brief.get("_clinical_facts", brief.get("rebuttal_seed", ""))
    employer = brief.get("employer_archetype")
    emp = f" The member is {employer}." if employer else ""

    ctx = (
        f"The {age}-year-old member has {brief['diagnosis']}.{emp} "
        f"{pronoun} has been treated under commercial coverage with {brief['treatment_requested']} "
        f"recommended as the next appropriate step. {facts} "
        f"This directly contradicts the insurer's position that {cell['sub_tactic'].replace('_', ' ')} "
        f"bars coverage: the chart documents dates, doses, and objective findings that were "
        f"submitted with the original request but are not reflected in the denial letter's rationale. "
        f"Treating clinicians note ongoing functional impairment and avoidable harm if {possessive} "
        f"care is delayed further."
    )
    return ctx.strip()
