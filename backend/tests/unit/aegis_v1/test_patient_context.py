from __future__ import annotations

import json
from pathlib import Path

from app.aegis_v1.patient_context import (
    compose_interactive_clinical_context,
    extract_patient_fields,
    format_patient_clinical_context,
    pipeline_inputs_from_case,
)
from app.aegis_v1.tools import case_parser


def test_compose_interactive_clinical_context_appends_optional_notes() -> None:
    ctx = compose_interactive_clinical_context(
        patient_age=49,
        patient_gender="F",
        clinical_notes="Failed two SSRIs; severe depression.",
    )
    assert ctx.startswith("Patient age: 49. Patient gender: female.")
    assert "Failed two SSRIs" in ctx


def test_format_patient_clinical_context_is_minimal() -> None:
    ctx = format_patient_clinical_context(patient_age=49, patient_gender="F")
    assert ctx == "Patient age: 49. Patient gender: female."
    assert "OCD" not in ctx


def test_pipeline_inputs_from_synthetic_case_metadata_only() -> None:
    case_path = (
        Path(__file__).resolve().parents[4]
        / "eval"
        / "cases"
        / "drafts"
        / "case_11_uhc_mednec.json"
    )
    case_obj = json.loads(case_path.read_text(encoding="utf-8"))
    inputs = pipeline_inputs_from_case(case_obj)

    assert inputs["insurer"] == "UnitedHealthcare"
    assert inputs["patient_age"] == 49
    assert inputs["patient_gender"] == "F"
    assert "failed" not in inputs["clinical_context"].lower()
    assert case_obj["clinical_context"] not in inputs["clinical_context"]


def test_case_parser_structured_without_notes_uses_minimal_context() -> None:
    parsed = case_parser(
        denial_text="UnitedHealthcare denied coverage. Appeal within 180 days.",
        clinical_context="",
        case_id="case_11_uhc_mednec",
        insurer="UHC",
        patient_age=49,
        patient_gender="F",
    )
    assert parsed["clinical_context"] == "Patient age: 49. Patient gender: female."


def test_case_parser_structured_preserves_optional_notes() -> None:
    parsed = case_parser(
        denial_text="UnitedHealthcare denied coverage. Appeal within 180 days.",
        clinical_context=compose_interactive_clinical_context(
            patient_age=49,
            patient_gender="F",
            clinical_notes="Failed compression therapy.",
        ),
        case_id="case_11_uhc_mednec",
        insurer="UHC",
        patient_age=49,
        patient_gender="F",
    )
    assert "Patient age: 49" in parsed["clinical_context"]
    assert "Failed compression therapy" in parsed["clinical_context"]
    assert parsed["insurer"] == "UnitedHealthcare"
    assert parsed["patient_age"] == 49
    assert parsed["patient_gender"] == "F"
    assert "clinical_context" not in parsed["missing_facts"]


def test_extract_patient_fields_from_student_case_shape() -> None:
    insurer, age, gender = extract_patient_fields(
        {
            "insurer": "Cigna",
            "patient_age": 34,
            "patient_gender": "M",
        }
    )
    assert insurer == "Cigna"
    assert age == 34
    assert gender == "M"
