from __future__ import annotations

import re
from typing import Any

from app.evals.part_a.schemas import JudgeResult
from app.evals.part_a.schemas import TeacherGradingPacket

_FAKE_DOC_ID_PATTERNS = [
    re.compile(r"fake", re.IGNORECASE),
    re.compile(r"9999"),
    re.compile(r"0000-"),
    re.compile(r"cpb-999", re.IGNORECASE),
]

_LETTER_INVENTED_SOURCE_PATTERNS = [
    re.compile(r"42\s*u\.s\.c\.?\s*9999", re.IGNORECASE),
    re.compile(r"aetna\s+cpb-9992x", re.IGNORECASE),
    re.compile(r"cigna\s+policy\s+0000-fake", re.IGNORECASE),
]


def _appeal_letter(appeal_package: dict[str, Any]) -> str:
    return str(appeal_package.get("appeal_package_draft", {}).get("appeal_letter", ""))


def faithfulness_citation_precheck(
    appeal_package: dict[str, Any],
    teacher: TeacherGradingPacket | None = None,
) -> JudgeResult:
    """Structural precheck for obvious invented sources in appeal letter prose.

    `citations_used` librarian metadata is intentionally ignored — thin BM25 retrieval
    can attach wrong-insurer docs the letter never cites. J2 scores letter prose only.
    """
    del teacher  # kept for call-site compatibility
    letter = _appeal_letter(appeal_package)
    failures: list[str] = []
    evidence: list[str] = []

    for pattern in _FAKE_DOC_ID_PATTERNS:
        match = pattern.search(letter)
        if match:
            failures.append(f"invented corpus document reference in letter: {match.group(0)}")
            evidence.append(match.group(0))
            break

    for pattern in _LETTER_INVENTED_SOURCE_PATTERNS:
        match = pattern.search(letter)
        if match:
            failures.append(f"obvious invented source in letter: {match.group(0)}")
            evidence.append(match.group(0))
            break

    if failures:
        return JudgeResult(
            dimension="citation_precheck",
            reasoning="Appeal-letter citation precheck failed: " + "; ".join(failures),
            score="FAIL",
            confidence=1.0,
            evidence_quotes=evidence,
            improvement="Remove fabricated sources from the appeal letter or correct the citation.",
        )

    return JudgeResult(
        dimension="citation_precheck",
        reasoning=(
            "No obvious invented sources in appeal letter prose. Structured "
            "citations_used metadata is not scored (librarian retrieval artifact)."
        ),
        score="PASS",
        confidence=1.0,
        evidence_quotes=[],
        improvement=None,
    )


def citation_precheck(
    appeal_package: dict[str, Any],
    teacher: TeacherGradingPacket,
) -> JudgeResult:
    """Backward-compatible alias for faithfulness_citation_precheck."""
    return faithfulness_citation_precheck(appeal_package, teacher)
