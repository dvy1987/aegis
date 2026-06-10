"""Slice identity for per-slice playbooks and GEPA learning.

A slice is insurer + denial pattern + sub_tactic, e.g.
``Cigna:medical_necessity:not_evidence_based``.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from app.aegis_v1.patient_context import normalize_insurer


class SliceParts(NamedTuple):
    insurer: str
    denial_type: str
    sub_tactic: str


def normalize_denial_type_for_slice(denial_type: str) -> str:
    from app.aegis_v1.tools import _normalize_denial_type

    normalized = _normalize_denial_type(denial_type.replace("_", " "))
    if normalized == "unknown":
        return denial_type.strip().lower().replace(" ", "_")
    return normalized


def normalize_insurer_for_slice(insurer: str) -> str:
    resolved = normalize_insurer(insurer)
    if resolved == "UHC":
        return "UnitedHealthcare"
    return resolved


def sub_tactic_from_case(case: dict[str, Any]) -> str:
    provenance = case.get("synthetic_provenance") or {}
    matrix_cell = provenance.get("matrix_cell") or {}
    sub = matrix_cell.get("sub_tactic")
    if isinstance(sub, str) and sub.strip():
        return sub.strip()
    return "unknown"


def format_slice_key(insurer: str, denial_type: str, sub_tactic: str) -> str:
    return (
        f"{normalize_insurer_for_slice(insurer)}:"
        f"{normalize_denial_type_for_slice(denial_type)}:"
        f"{(sub_tactic or 'unknown').strip()}"
    )


def parse_slice_key(slice_key: str) -> SliceParts:
    parts = slice_key.split(":", 2)
    if len(parts) != 3:
        raise ValueError(
            f"Invalid slice key {slice_key!r}; expected insurer:denial_type:sub_tactic"
        )
    return SliceParts(parts[0], parts[1], parts[2])


def playbook_component_id(slice_key: str) -> str:
    return f"playbook:{slice_key}"


def playbook_filename(insurer: str, denial_type: str, sub_tactic: str) -> str:
    from app.aegis_v1.tools import _slug

    base = f"{_slug(insurer)}__{normalize_denial_type_for_slice(denial_type)}"
    tactic = (sub_tactic or "unknown").strip()
    if tactic and tactic != "unknown":
        return f"{base}__{_slug(tactic)}.json"
    return f"{base}.json"
