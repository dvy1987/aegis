from __future__ import annotations

import re
from dataclasses import dataclass

_REDACTED = "[REDACTED]"

_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_DOB = re.compile(
    r"\b(?:DOB|Date of Birth)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    re.IGNORECASE,
)
_MEMBER_ID = re.compile(
    r"\b(?:Member ID|Subscriber ID|Policy ID)[:\s#]*[A-Z0-9-]{6,}\b",
    re.IGNORECASE,
)
_MRN = re.compile(r"\b(?:MRN|Medical Record)[:\s#]*[A-Z0-9-]{5,}\b", re.IGNORECASE)
_PATIENT_LINE = re.compile(
    r"^(Patient|Member|Subscriber):\s*.+$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted_fields: tuple[str, ...]


def redact_identifiers(text: str) -> RedactionResult:
    """Rule-based PHI strip for Phoenix export copies (/appeal path only)."""
    redacted_fields: list[str] = []
    out = text

    for label, pattern in (
        ("ssn", _SSN),
        ("phone", _PHONE),
        ("email", _EMAIL),
        ("dob", _DOB),
        ("member_id", _MEMBER_ID),
        ("mrn", _MRN),
        ("patient_line", _PATIENT_LINE),
    ):
        if pattern.search(out):
            redacted_fields.append(label)
            out = pattern.sub(_REDACTED, out)

    return RedactionResult(text=out, redacted_fields=tuple(redacted_fields))
