"""Shared neighbour summaries for P5 diversity (A+ and legacy pipelines)."""

from __future__ import annotations

from typing import Any


def neighbour_summary(case: dict[str, Any]) -> str:
    mc = case["synthetic_provenance"]["matrix_cell"]
    return (
        f"- [{mc['insurer']} / {mc['denial_type']} / {mc['specialty']} / "
        f"{mc['sub_tactic']}] dx={case['patient_profile']['diagnosis']}; "
        f"tx={case['patient_profile']['treatment_requested']}"
    )
