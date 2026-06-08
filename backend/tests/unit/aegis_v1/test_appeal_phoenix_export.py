from __future__ import annotations

from app.aegis_v1.appeal_phoenix_export import (
    build_redacted_appeal_package,
    in_memory_recorder,
    write_appeal_phoenix_export,
)
from app.aegis_v1.phoenix_mode import PhoenixMode

PACKAGE = {
    "run_id": "test-run",
    "parsed_case": {
        "case_id": "appeal-1",
        "insurer": "Cigna",
        "denial_type": "medical_necessity",
        "plan_type": "commercial",
        "service_or_procedure": "IOP",
        "diagnosis_summary": "OCD",
        "state": "CA",
        "cited_denial_reason": "not necessary",
        "denial_text": "Patient: Jordan Lee denied IOP.",
        "clinical_context": "Severe OCD with six-hour compulsions.",
    },
    "appeal_package_draft": {
        "appeal_letter": (
            "Patient: Jordan Lee\nMember ID: CIG-123\n"
            "Clinical: severe OCD requiring IOP for six hours daily compulsions."
        ),
    },
    "self_check": {"status": "ok", "risk_flags": []},
    "risk_flags": [],
    "trace_metadata": {"case_id": "appeal-1", "insurer": "Cigna"},
}


def test_build_redacted_appeal_package_strips_identifiers() -> None:
    redacted = build_redacted_appeal_package(
        PACKAGE,
        denial_text="Patient: Jordan Lee",
        clinical_context="Phone: 555-123-4567",
        use_scrubber=False,
    )
    letter = redacted["appeal_package_draft"]["appeal_letter"]
    assert "Jordan Lee" not in letter
    assert "CIG-123" not in letter
    assert "severe OCD" in letter
    assert "six hours" in letter or "six-hour" in letter


def test_write_appeal_phoenix_export_skips_holdout_mode() -> None:
    recorder = in_memory_recorder()
    ref = write_appeal_phoenix_export(
        PACKAGE,
        recorder=recorder,
        use_scrubber=False,
        phoenix_mode=PhoenixMode.HOLDOUT_READONLY,
    )
    assert ref is None
    assert recorder._runs == {}


def test_write_appeal_phoenix_export_uses_redacted_copy() -> None:
    recorder = in_memory_recorder()
    ref = write_appeal_phoenix_export(
        PACKAGE,
        denial_text="Patient: Jordan Lee",
        clinical_context="",
        recorder=recorder,
        use_scrubber=False,
    )
    assert ref is not None
    stored = recorder.get(ref)
    letter = stored["appeal_package"]["appeal_package_draft"]["appeal_letter"]
    assert "Jordan Lee" not in letter
    assert stored["metadata"]["memory_eligible"] == "true"
    assert stored["metadata"]["phoenix_mode"] == "appeal"
    assert stored["metadata"]["redacted_export"] == "true"
