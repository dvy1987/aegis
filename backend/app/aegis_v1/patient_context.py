from __future__ import annotations

from typing import Any

_GENDER_LABELS = {
    "F": "female",
    "M": "male",
    "X": "non-binary",
}


def normalize_insurer(insurer: str) -> str:
    """Map wire-form insurer keys to the canonical playbook / trace name."""
    key = (insurer or "").strip()
    lowered = key.lower()
    if lowered in {"uhc", "unitedhealthcare", "united healthcare"}:
        return "UnitedHealthcare"
    if lowered == "aetna":
        return "Aetna"
    if lowered == "cigna":
        return "Cigna"
    return key or "unknown"


def normalize_gender(gender: str) -> str:
    raw = (gender or "").strip().upper()
    if raw in _GENDER_LABELS:
        return raw
    if raw in {"FEMALE", "WOMAN"}:
        return "F"
    if raw in {"MALE", "MAN"}:
        return "M"
    if raw in {"NON-BINARY", "NONBINARY", "NB"}:
        return "X"
    return raw[:1] if raw else ""


def format_patient_clinical_context(*, patient_age: int, patient_gender: str) -> str:
    """Minimal drafter context: age and gender only (no free-form clinical notes)."""
    gender_key = normalize_gender(patient_gender)
    label = _GENDER_LABELS.get(gender_key, patient_gender or "unspecified")
    return f"Patient age: {patient_age}. Patient gender: {label}."


def compose_interactive_clinical_context(
    *,
    patient_age: int,
    patient_gender: str,
    clinical_notes: str = "",
) -> str:
    """Structured age/gender plus optional free-form notes for the /appeal path."""
    base = format_patient_clinical_context(
        patient_age=patient_age,
        patient_gender=patient_gender,
    )
    notes = clinical_notes.strip()
    if not notes:
        return base
    return f"{base}\n\n{notes}"


def extract_patient_fields(case_obj: dict[str, Any]) -> tuple[str, int, str]:
    insurer = normalize_insurer(str(case_obj.get("insurer") or "unknown"))
    profile = case_obj.get("patient_profile") or {}
    age_raw = case_obj.get("patient_age", profile.get("age"))
    gender_raw = case_obj.get("patient_gender", profile.get("gender"))
    try:
        age = int(age_raw) if age_raw is not None else 0
    except (TypeError, ValueError):
        age = 0
    gender = normalize_gender(str(gender_raw or ""))
    return insurer, age, gender


def pipeline_inputs_from_case(case_obj: dict[str, Any]) -> dict[str, Any]:
    """Build Student pipeline inputs from a synthetic case object or student_case dict."""
    insurer, age, gender = extract_patient_fields(case_obj)
    return {
        "denial_text": str(case_obj.get("denial_letter_text") or ""),
        "clinical_context": format_patient_clinical_context(
            patient_age=age,
            patient_gender=gender,
        ),
        "case_id": str(case_obj.get("case_id") or "interactive_case"),
        "insurer": insurer,
        "patient_age": age,
        "patient_gender": gender,
    }
