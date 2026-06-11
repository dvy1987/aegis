"""De-duplicate patient-facing gap questions by theme (question agent + mirror UI)."""
from __future__ import annotations

import re

_THEME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "doctor_letter",
        re.compile(
            r"letter|formulary exception|prescriber|oncologist.*sent|supporting letter|"
            r"why you need|why it is not appropriate|preferred alternatives",
            re.I,
        ),
    ),
    (
        "preferred_alt",
        re.compile(r"preferred alternative|which medication|step therapy|non-preferred", re.I),
    ),
    (
        "clinical_records",
        re.compile(r"records|labs|imaging|office notes|documentation|clinical", re.I),
    ),
    (
        "prior_auth",
        re.compile(r"prior auth|prior authorization", re.I),
    ),
    (
        "med_necessity",
        re.compile(r"medically necessary|medical necessity|experimental|investigational", re.I),
    ),
]


def _theme(text: str) -> str:
    for name, pattern in _THEME_PATTERNS:
        if pattern.search(text):
            return name
    return "other"


def dedupe_gap_questions(gap_questions: list[str], *, max_items: int = 4) -> list[str]:
    """Keep at most one unresolved gap per theme; preserve first-seen order."""
    seen_themes: set[str] = set()
    out: list[str] = []
    for question in gap_questions:
        q = question.strip()
        if not q:
            continue
        theme = _theme(q)
        if theme != "other" and theme in seen_themes:
            continue
        if theme != "other":
            seen_themes.add(theme)
        out.append(q)
        if len(out) >= max_items:
            break
    return out
