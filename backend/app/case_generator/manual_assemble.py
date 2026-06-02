"""Assemble schema-valid synthetic cases from manual (non-Vertex) swarm outputs.

Used when Cursor/agent intelligence executes each producer and critic per the
prompt templates in ``prompts/``, instead of ``agents._generate_json``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from . import config
from .manual_batches.matrix_planner import benchmark_public_number
from .prompts import PROMPT_VERSIONS
from .safety import scan_banned, scan_phi
from .validator import validate_case

MANUAL_GENERATOR_MODEL = "cursor-manual-agent-2026-06-01"


def new_run_id(batch: int) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"manual-b{batch:02d}-{stamp}-{uuid.uuid4().hex[:5]}"


def _case_id_for(insurer: str, denial_type: str, index: int, *, matrix_index: int | None = None) -> str:
    short = "mednec" if denial_type == "Medical Necessity" else "priorauth"
    pub = benchmark_public_number(matrix_index) if matrix_index is not None else index
    return f"case_{pub:02d}_{insurer.lower()}_{short}"


def _phi_verdict(denial_letter_text: str, clinical_context: str) -> dict[str, Any]:
    hits = scan_phi(denial_letter_text + "\n" + clinical_context)
    if hits:
        return {
            "dimension": "phi_pii",
            "reasoning": "Deterministic PHI patterns detected: "
            + ", ".join(f"{h.label}:{h.matched_text}" for h in hits),
            "score": "FAIL",
            "confidence": 1.0,
            "evidence_quotes": [h.matched_text for h in hits],
            "improvement": "Strip PHI patterns from generated text.",
        }
    return {
        "dimension": "phi_pii",
        "reasoning": "No deterministic PHI patterns detected.",
        "score": "PASS",
        "confidence": 1.0,
        "evidence_quotes": [],
        "improvement": None,
    }


def _safety_verdict(denial_letter_text: str, clinical_context: str) -> dict[str, Any]:
    hits = scan_banned(denial_letter_text + "\n" + clinical_context)
    if hits:
        return {
            "dimension": "safety_redactor",
            "reasoning": "Deterministic regex matched banned topic(s): "
            + ", ".join(f"{h.topic_id}:{h.matched_text}" for h in hits),
            "score": "FAIL",
            "confidence": 1.0,
            "evidence_quotes": [h.matched_text for h in hits],
            "improvement": "Re-roll scenario; do not include banned content.",
        }
    return {
        "dimension": "safety_redactor",
        "reasoning": (
            "Commercial-plan denial for an in-scope insurer with no banned-topic "
            "language, no violence, and no out-of-scope programs."
        ),
        "score": "PASS",
        "confidence": 0.95,
        "evidence_quotes": [],
        "improvement": None,
    }


def assemble_case(
    *,
    index: int,
    matrix_cell: dict[str, str],
    patient_profile: dict[str, Any],
    denial_letter_text: str,
    clinical_context: str,
    denial_pattern_sources: list[str],
    denial_letter_references: list[dict[str, str]] | None = None,
    critic_verdicts: dict[str, dict[str, Any]],
    run_id: str,
    case_id: str | None = None,
    submission_timestamp: str | None = None,
    denial_timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a case dict and run deterministic gates + JSON Schema validation."""
    safety_v = _safety_verdict(denial_letter_text, clinical_context)
    phi_v = _phi_verdict(denial_letter_text, clinical_context)
    if safety_v["score"] == "FAIL" or phi_v["score"] == "FAIL":
        raise ValueError(
            f"Deterministic gate failed for case index {index}: "
            f"safety={safety_v['score']} phi={phi_v['score']}"
        )

    all_critics = {**critic_verdicts, "safety_redactor": safety_v, "phi_pii": phi_v}
    appeal = all_critics.get("appeal_difficulty", {})
    provenance: dict[str, Any] = {
        "generator_model": MANUAL_GENERATOR_MODEL,
        "run_id": run_id,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matrix_cell": matrix_cell,
        "prompt_versions": PROMPT_VERSIONS,
        "banned_topic_filter_version": config.banned_filter_version(),
        "schema_version": config.schema_version(),
        "diversity_matrix_version": config.matrix_version(),
        "critic_verdicts": all_critics,
        "human_summary": (
            f"Manual swarm case for {matrix_cell['insurer']} {matrix_cell['denial_type']} / "
            f"{matrix_cell['specialty']} / sub_tactic={matrix_cell['sub_tactic']}. "
            "Producers and critics executed by Cursor agent intelligence (no Vertex Gemini)."
        ),
        "appeal_difficulty": {
            "score": appeal.get("score", 3),
            "reasoning": appeal.get("reasoning", ""),
            "exploitable_weaknesses": appeal.get("exploitable_weaknesses", []),
            "strong_defenses": appeal.get("strong_defenses", []),
        },
    }
    case_obj = {
        "case_id": case_id
        or _case_id_for(
            matrix_cell["insurer"],
            matrix_cell["denial_type"],
            index,
            matrix_index=index,
        ),
        "insurer": matrix_cell["insurer"],
        "denial_type": matrix_cell["denial_type"],
        "patient_profile": patient_profile,
        "denial_pattern_sources": denial_pattern_sources,
        "denial_letter_references": denial_letter_references or [],
        "denial_letter_text": denial_letter_text,
        "clinical_context": clinical_context,
        "submission_timestamp": submission_timestamp,
        "denial_timestamp": denial_timestamp,
        "synthetic_provenance": provenance,
    }
    result = validate_case(case_obj)
    if not result.ok:
        raise ValueError(f"Schema validation failed for {case_obj['case_id']}: {result.errors}")
    return case_obj
