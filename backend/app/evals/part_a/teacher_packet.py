from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.evals.part_a.schemas import (
    CorpusExcerpt,
    StudentCasePacket,
    TeacherGradingPacket,
)

REPO_ROOT = Path(os.environ.get("AEGIS_REPO_ROOT", Path(__file__).resolve().parents[4]))
DENIAL_PATTERNS_PATH = REPO_ROOT / "eval" / "denial_patterns.json"


def _load_denial_patterns() -> list[dict[str, Any]]:
    if not DENIAL_PATTERNS_PATH.exists():
        return []
    with DENIAL_PATTERNS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh).get("patterns", [])


def _pattern_matches_source(pattern: dict[str, Any], source: str) -> bool:
    source_norm = source.strip().lower()
    source_id = source_norm.split(":", 1)[0].strip()
    if not source_norm:
        return False
    candidates = [
        pattern.get("id", ""),
        pattern.get("source", ""),
        pattern.get("description", ""),
        pattern.get("category", ""),
    ]
    return any(
        source_norm == str(candidate).strip().lower()
        or source_id == str(candidate).strip().lower()
        for candidate in candidates
    )


def _expected_vectors_for_sources(sources: list[str]) -> list[str]:
    vectors: list[str] = []
    patterns = _load_denial_patterns()
    for source in sources:
        for pattern in patterns:
            if _pattern_matches_source(pattern, source):
                vector = pattern.get("appeal_vector")
                if vector:
                    vectors.append(str(vector))
    return list(dict.fromkeys(vectors))


def _corpus_excerpts_from_appeal_package(
    appeal_package: dict[str, Any] | None,
) -> list[CorpusExcerpt]:
    if not appeal_package:
        return []
    draft = appeal_package.get("appeal_package_draft", {})
    excerpts: list[CorpusExcerpt] = []
    for hit in draft.get("citations_used", []) or []:
        doc_id = str(hit.get("corpus_doc_id", ""))
        quote = str(hit.get("quote", ""))
        if doc_id and quote:
            excerpts.append(
                CorpusExcerpt(
                    corpus_doc_id=doc_id,
                    title=str(hit.get("title", "")),
                    quote=quote,
                )
            )
    return excerpts


def build_student_case_packet(case_obj: dict[str, Any]) -> StudentCasePacket:
    """Build the packet the runtime student is allowed to see."""

    return StudentCasePacket(
        case_id=str(case_obj.get("case_id", "unknown_case")),
        denial_letter_text=str(case_obj.get("denial_letter_text", "")),
        clinical_context=str(case_obj.get("clinical_context", "")),
    )


def build_teacher_grading_packet(
    case_obj: dict[str, Any],
    appeal_package: dict[str, Any] | None = None,
) -> TeacherGradingPacket:
    """Build the teacher-only grading packet from a generated case."""

    provenance = case_obj.get("synthetic_provenance", {}) or {}
    difficulty = provenance.get("appeal_difficulty", {}) or {}
    sources = list(case_obj.get("denial_pattern_sources", []) or [])
    expected_vectors = _expected_vectors_for_sources(sources)
    exploitable = list(difficulty.get("exploitable_weaknesses", []) or [])
    strong_defenses = list(difficulty.get("strong_defenses", []) or [])
    denial_letter_references = [
        ref for ref in list(case_obj.get("denial_letter_references", []) or [])
        if isinstance(ref, dict)
    ]
    risk_flags: list[str] = []

    matrix_cell = provenance.get("matrix_cell", {}) or {}
    if not expected_vectors:
        expected_vectors = exploitable.copy()
    if not expected_vectors or any(value == "unknown" for value in matrix_cell.values()):
        risk_flags.append("weak_teacher_packet")
    if "Legacy manual generation" in sources:
        risk_flags.append("legacy_case_provenance")

    return TeacherGradingPacket(
        case_id=str(case_obj.get("case_id", "unknown_case")),
        insurer=str(case_obj.get("insurer", "")),
        denial_type=str(case_obj.get("denial_type", "")),
        patient_profile=dict(case_obj.get("patient_profile", {}) or {}),
        denial_letter_text=str(case_obj.get("denial_letter_text", "")),
        clinical_context=str(case_obj.get("clinical_context", "")),
        matrix_cell=dict(matrix_cell),
        denial_pattern_sources=sources,
        denial_letter_references=denial_letter_references,
        expected_appeal_vectors=list(dict.fromkeys(expected_vectors)),
        exploitable_weaknesses=exploitable,
        strong_defenses=strong_defenses,
        submission_timestamp=case_obj.get("submission_timestamp"),
        denial_timestamp=case_obj.get("denial_timestamp"),
        corpus_excerpts=_corpus_excerpts_from_appeal_package(appeal_package),
        risk_flags=risk_flags,
    )


def load_case(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)
