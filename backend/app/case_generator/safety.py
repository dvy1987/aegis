from __future__ import annotations

import re
from dataclasses import dataclass

from .config import load_banned


@dataclass
class SafetyHit:
    topic_id: str
    label: str
    matched_text: str


_PHI_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN"),
    (re.compile(r"\bMRN\s*#?:?\s*\w+\b", re.IGNORECASE), "MRN"),
    (
        re.compile(r"\bDOB\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
        "DOB",
    ),
]


def scan_banned(text: str) -> list[SafetyHit]:
    hits: list[SafetyHit] = []
    banned = load_banned()
    for topic in banned["banned_topics"]:
        for pat in topic.get("deterministic_patterns", []):
            m = re.search(pat, text)
            if m:
                hits.append(
                    SafetyHit(
                        topic_id=topic["topic_id"],
                        label=topic["label"],
                        matched_text=m.group(0),
                    )
                )
    return hits


def scan_phi(text: str) -> list[SafetyHit]:
    hits: list[SafetyHit] = []
    for pat, label in _PHI_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append(SafetyHit(topic_id="phi", label=label, matched_text=m.group(0)))
    return hits


def banned_topic_briefs() -> str:
    return "\n".join(
        f"- {t['topic_id']}: {t['label']} — {t['llm_check_guidance']}"
        for t in load_banned()["banned_topics"]
    )
